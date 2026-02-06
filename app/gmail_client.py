from __future__ import annotations

import base64
import os
import re
import logging
from typing import Dict, List, Tuple, Optional

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
    """Kapselt Authentifizierung und Kern-Operationen gegen die Gmail API."""

    def __init__(self) -> None:
        self.service = self._auth()

    def _auth(self):
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as f:
                f.write(creds.to_json())
        return build("gmail", "v1", credentials=creds)

    def ensure_labels(self, names: List[str], colors: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, str]:
        """Stellt sicher, dass alle gewünschten User-Labels existieren und setzt optional Farben.

        colors: Mapping Labelname -> {"backgroundColor": "#RRGGBB", "textColor": "#RRGGBB"}
        """
        existing = self.service.users().labels().list(userId="me").execute().get("labels", [])
        name_to_id = {l["name"]: l["id"] for l in existing if l.get("type") == "user"}
        for name in names:
            if name not in name_to_id:
                # Immer ohne Farbe anlegen, Farben separat per Patch setzen
                body = {"name": name}
                lab = self.service.users().labels().create(userId="me", body=body).execute()
                name_to_id[name] = lab["id"]

        # Für bestehende Labels ggf. Farben per Patch setzen
        if colors:
            for name, color in colors.items():
                if name in name_to_id:
                    self._try_set_label_color(name_to_id[name], name, color)

        return name_to_id

    def _try_set_label_color(self, label_id: str, label_name: str, desired: Dict[str, str]) -> None:
        """Versucht, eine Farbe zu setzen. Fällt bei Palette-Fehlern auf erlaubte Werte zurück."""
        try:
            self.service.users().labels().patch(
                userId="me",
                id=label_id,
                body={"color": desired},
            ).execute()
            return
        except HttpError as e:
            msg = str(e)
            if "allowed color palette" not in msg:
                logger.warning("Konnte Farbe für Label '%s' nicht setzen: %s", label_name, e)
                return

        # Fallback: wähle startindex deterministisch pro Label, damit unterschiedliche Farben entstehen
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
                    logger.info("Label '%s' Farbe gesetzt auf bg=%s txt=%s (Fallback)", label_name, bg, txt)
                    return
                except HttpError:
                    continue
        logger.warning("Keine kompatible Farbe für Label '%s' gefunden; verwende Standard.", label_name)

    def list_new_message_ids(self, q: str, max_results: int = 20) -> List[str]:
        """Listet bis zu `max_results` Nachrichten-IDs mit Pagination auf."""
        collected: List[str] = []
        page_token: Optional[str] = None
        while True:
            batch_max = max_results - len(collected)
            if batch_max <= 0:
                break
            res = self.service.users().messages().list(
                userId="me", q=q, maxResults=min(100, batch_max), pageToken=page_token
            ).execute()
            msgs = res.get("messages", [])
            collected.extend([m["id"] for m in msgs])
            page_token = res.get("nextPageToken")
            if not page_token or not msgs:
                break
        return collected[:max_results]

    def fetch_message_core(self, msg_id: str) -> Tuple[str, str, str, List[str], int]:
        msg = self.service.users().messages().get(userId="me", id=msg_id, format="full").execute()
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
                        # Einfache HTML->Text Konvertierung
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
        try:
            self.service.users().messages().batchModify(
                userId="me",
                body={"ids": message_ids, "addLabelIds": add_label_ids},
            ).execute()
        except HttpError as e:
            logger.error("batchModify fehlgeschlagen: %s", e)
            raise

    def batch_modify(self, message_ids: List[str], add_label_ids: Optional[List[str]] = None, remove_label_ids: Optional[List[str]] = None) -> None:
        if not message_ids:
            return
        body: Dict[str, List[str]] = {"ids": message_ids}
        if add_label_ids:
            body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids
        try:
            self.service.users().messages().batchModify(userId="me", body=body).execute()
        except HttpError as e:
            logger.error("batchModify (add/remove) fehlgeschlagen: %s", e)
            raise


