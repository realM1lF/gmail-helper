from __future__ import annotations

import base64
import os
import re
import logging
from typing import Dict, List, Tuple, Optional

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow


logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Konservative Gmail-Palette (bekannte funktionierende Werte)
ALLOWED_LABEL_COLORS = [
    "#7bd148", "#5484ed", "#a4bdfc", "#46d6db", "#7ae7bf",
    "#51b749", "#fbd75b", "#ffb878", "#ff887c", "#dc2127",
    "#dbadff", "#e1e1e1", "#b3dc6c", "#c2c2c2", "#9fc6e7",
    "#4986e7", "#cabdbf", "#ac725e", "#cd74e6", "#cca6ac",
]


class GmailClient:
    """Kapselt Authentifizierung und Kern-Operationen gegen die Gmail API.
    
    Implementiert automatischen Token-Refresh für Dauerbetrieb im Loop-Modus.
    """

    def __init__(self) -> None:
        self._creds: Optional[Credentials] = None
        self.service = self._auth()

    def _load_credentials(self) -> Optional[Credentials]:
        """Lädt Credentials aus token.json wenn vorhanden."""
        if os.path.exists("token.json"):
            return Credentials.from_authorized_user_file("token.json", SCOPES)
        return None

    def _save_credentials(self, creds: Credentials) -> None:
        """Speichert Credentials in token.json."""
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    def _refresh_credentials(self, creds: Credentials) -> Credentials:
        """Refresht abgelaufene Credentials wenn möglich."""
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token ist abgelaufen, refreshe...")
            creds.refresh(Request())
            self._save_credentials(creds)
            logger.info("Token erfolgreich refreshed.")
        return creds

    def _authenticate_new(self) -> Credentials:
        """Führt neue OAuth-Authentifizierung durch."""
        logger.info("Starte neue OAuth-Authentifizierung...")
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        self._save_credentials(creds)
        logger.info("Neue Authentifizierung erfolgreich.")
        return creds

    def _auth(self) -> build:
        """Authentifiziert und erstellt den Gmail Service.
        
        Versucht zuerst bestehende Credentials zu laden und zu refreshen.
        Bei ungültigen/keinen Credentials wird neue Authentifizierung durchgeführt.
        """
        creds = self._load_credentials()
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds = self._refresh_credentials(creds)
            else:
                creds = self._authenticate_new()
        
        self._creds = creds
        return build("gmail", "v1", credentials=creds)

    def _ensure_valid_credentials(self) -> None:
        """Stellt sicher, dass Credentials gültig sind vor API-Calls.
        
        Wird vor jedem API-Call aufgerufen um abgelaufene Tokens zu erkennen
        und automatisch zu refreshen. Bei 401-Fehlern wird Re-Authentifizierung erzwungen.
        """
        if not self._creds:
            logger.warning("Keine Credentials vorhanden, erstelle Service neu...")
            self.service = self._auth()
            return

        # Prüfe ob Token abgelaufen oder kurz vor Ablauf (< 5 Minuten)
        if not self._creds.valid or (self._creds.expiry and self._creds.expired):
            logger.info("Credentials ungültig oder abgelaufen, refreshe...")
            if self._creds.refresh_token:
                try:
                    self._creds.refresh(Request())
                    self._save_credentials(self._creds)
                    # Service mit neuen Credentials neu erstellen
                    self.service = build("gmail", "v1", credentials=self._creds)
                    logger.info("Credentials refreshed und Service neu erstellt.")
                except Exception as e:
                    logger.error("Token-Refresh fehlgeschlagen: %s", e)
                    # Bei Refresh-Fehler: Neue Authentifizierung erzwingen
                    self.service = self._auth()
            else:
                logger.warning("Kein refresh_token vorhanden, neue Authentifizierung...")
                self.service = self._auth()

    def _handle_api_error(self, error: HttpError) -> bool:
        """Behandelt API-Fehler und versucht Re-Authentifizierung bei 401.
        
        Returns:
            True wenn Retry möglich ist, False bei nicht behebbarem Fehler.
        """
        if error.resp.status == 401:
            logger.warning("401 Unauthorized erhalten, erzwinge Re-Authentifizierung...")
            self.service = self._auth()
            return True
        return False

    def ensure_labels(self, names: List[str], colors: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, str]:
        """Stellt sicher, dass alle gewünschten User-Labels existieren und setzt optional Farben.

        colors: Mapping Labelname -> {"backgroundColor": "#RRGGBB", "textColor": "#RRGGBB"}
        """
        self._ensure_valid_credentials()
        
        try:
            existing = self.service.users().labels().list(userId="me").execute().get("labels", [])
        except HttpError as e:
            if self._handle_api_error(e):
                # Retry nach Re-Authentifizierung
                existing = self.service.users().labels().list(userId="me").execute().get("labels", [])
            else:
                raise
        
        name_to_id = {l["name"]: l["id"] for l in existing if l.get("type") == "user"}
        for name in names:
            if name not in name_to_id:
                # Immer ohne Farbe anlegen, Farben separat per Patch setzen
                body = {"name": name}
                try:
                    lab = self.service.users().labels().create(userId="me", body=body).execute()
                    name_to_id[name] = lab["id"]
                except HttpError as e:
                    if self._handle_api_error(e):
                        lab = self.service.users().labels().create(userId="me", body=body).execute()
                        name_to_id[name] = lab["id"]
                    else:
                        raise

        # Für bestehende Labels ggf. Farben per Patch setzen
        if colors:
            for name, color in colors.items():
                if name in name_to_id:
                    self._try_set_label_color(name_to_id[name], name, color)

        return name_to_id

    def _try_set_label_color(self, label_id: str, label_name: str, desired: Dict[str, str]) -> None:
        """Setzt eine Farbe aus der Gmail-Palette (nur ALLOWED_LABEL_COLORS)."""
        self._ensure_valid_credentials()
        start = abs(hash(label_name)) % len(ALLOWED_LABEL_COLORS)
        order = ALLOWED_LABEL_COLORS[start:] + ALLOWED_LABEL_COLORS[:start]
        for bg in order:
            for txt in ("#000000", "#ffffff"):
                try:
                    self.service.users().labels().patch(
                        userId="me",
                        id=label_id,
                        body={"color": {"backgroundColor": bg, "textColor": txt}},
                    ).execute()
                    logger.info("Label '%s' Farbe gesetzt auf bg=%s txt=%s", label_name, bg, txt)
                    return
                except HttpError as e:
                    if e.resp.status == 401:
                        if self._handle_api_error(e):
                            continue  # Retry mit neuem Service
                    continue
        logger.warning("Keine kompatible Farbe für Label '%s' gefunden; verwende Standard.", label_name)

    def list_new_message_ids(self, q: str, max_results: int = 20) -> List[str]:
        """Listet bis zu `max_results` Nachrichten-IDs mit Pagination auf."""
        self._ensure_valid_credentials()
        collected: List[str] = []
        page_token: Optional[str] = None
        while True:
            batch_max = max_results - len(collected)
            if batch_max <= 0:
                break
            try:
                res = self.service.users().messages().list(
                    userId="me", q=q, maxResults=min(100, batch_max), pageToken=page_token
                ).execute()
            except HttpError as e:
                if self._handle_api_error(e):
                    # Retry nach Re-Authentifizierung
                    res = self.service.users().messages().list(
                        userId="me", q=q, maxResults=min(100, batch_max), pageToken=page_token
                    ).execute()
                else:
                    raise
            msgs = res.get("messages", [])
            collected.extend([m["id"] for m in msgs])
            page_token = res.get("nextPageToken")
            if not page_token or not msgs:
                break
        return collected[:max_results]

    def fetch_message_core(self, msg_id: str) -> Tuple[str, str, str, List[str], int]:
        self._ensure_valid_credentials()
        try:
            msg = self.service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        except HttpError as e:
            if self._handle_api_error(e):
                msg = self.service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            else:
                raise
        payload = msg.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        subject = headers.get("Subject", "")
        sender = headers.get("From", "")
        label_ids = msg.get("labelIds", [])
        internal_ts = int(msg.get("internalDate", 0))

        body_accum = []

        def walk(part):
            if not part:
                return
            parts = part.get("parts")
            if parts:
                for sub in parts:
                    walk(sub)
            mime = part.get("mimeType", "")
            data = part.get("body", {}).get("data")
            if data and (mime.startswith("text/plain") or mime.startswith("text/html")):
                try:
                    decoded = base64.urlsafe_b64decode(data).decode(errors="ignore")
                    if mime.startswith("text/html"):
                        # HTML->Text Konvertierung mit BeautifulSoup (Fallback auf Regex)
                        if HAS_BS4:
                            soup = BeautifulSoup(decoded, 'html.parser')
                            decoded = soup.get_text(separator=' ', strip=True)
                        else:
                            # Fallback: Einfache Regex-basierte Bereinigung
                            text = re.sub(r"<\s*br\s*/?>", "\n", decoded, flags=re.I)
                            text = re.sub(r"<\s*/p\s*>", "\n", text, flags=re.I)
                            text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
                            text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
                            text = re.sub(r"<[^>]+>", " ", text)
                            decoded = text
                    body_accum.append(decoded)
                except Exception:
                    pass

        walk(payload)
        body = " ".join(body_accum).strip()
        if not body:
            body = msg.get("snippet", "")
        body = re.sub(r"\s+", " ", body).strip()
        if len(body) > 4000:
            body = body[:4000]
        return subject, sender, body, label_ids, internal_ts

    def batch_add_labels(self, message_ids: List[str], add_label_ids: List[str]) -> None:
        if not message_ids:
            return
        self._ensure_valid_credentials()
        try:
            self.service.users().messages().batchModify(
                userId="me",
                body={"ids": message_ids, "addLabelIds": add_label_ids},
            ).execute()
        except HttpError as e:
            if self._handle_api_error(e):
                self.service.users().messages().batchModify(
                    userId="me",
                    body={"ids": message_ids, "addLabelIds": add_label_ids},
                ).execute()
            else:
                logger.error("batchModify fehlgeschlagen: %s", e)
                raise

    def batch_modify(self, message_ids: List[str], add_label_ids: Optional[List[str]] = None, remove_label_ids: Optional[List[str]] = None) -> None:
        if not message_ids:
            return
        self._ensure_valid_credentials()
        body: Dict[str, List[str]] = {"ids": message_ids}
        if add_label_ids:
            body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids
        try:
            self.service.users().messages().batchModify(userId="me", body=body).execute()
        except HttpError as e:
            if self._handle_api_error(e):
                self.service.users().messages().batchModify(userId="me", body=body).execute()
            else:
                logger.error("batchModify (add/remove) fehlgeschlagen: %s", e)
                raise


