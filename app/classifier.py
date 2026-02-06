from __future__ import annotations

import json
import logging
from typing import List

import httpx
import time

from .utils import heuristic_labels


def _extract_labels_json(text: str) -> dict | None:
    """Extrahiert ein JSON-Objekt mit Key 'labels' aus Text (Fallback wenn Modell um JSON herum schreibt)."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Ein JSON-Objekt mit "labels" im Text suchen (balancierte Klammern)
    idx = text.find('"labels"')
    if idx == -1:
        idx = text.find("'labels'")
    if idx >= 0:
        start = text.rfind("{", 0, idx + 1)
    else:
        start = -1
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


logger = logging.getLogger(__name__)


class Classifier:
    """Klassifiziert E-Mails per Ollama (lokal) und liefert strukturierte Label-Ausgaben."""

    def __init__(
        self,
        labels_allowed: List[str],
        ollama_base_url: str | None = None,
        ollama_model: str | None = None,
    ):
        self.labels_allowed = labels_allowed
        self.ollama_base_url = ollama_base_url or "http://localhost:11434"
        self.ollama_model = ollama_model or "qwen2.5:7b-instruct"

    def classify(self, sender: str, subject: str, body: str) -> List[str]:
        ai_labels = self._classify_via_ollama(sender, subject, body)
        if ai_labels == ["Sonstiges"] or not ai_labels:
            heur = heuristic_labels(subject, sender, body)
            if heur:
                logger.debug("Heuristik-Fallback: %s | %s -> %s", subject[:80], sender, ", ".join(heur))
                return heur
        return ai_labels

    def _ollama_messages(self, sender: str, subject: str, body: str) -> list:
        """System- und Few-Shot-Nachrichten für Ollama."""
        # Kriterienbasiert: Label nur bei eindeutigem Kriterien-Match; sonst nur Sonstiges (nie kombiniert)
        default_rule = (
            "Prüfe für jede Kategorie: Erfüllt diese E-Mail die definierenden Kriterien **eindeutig**? "
            "Nur wenn ja → das passende Label. Erfüllt sie **keine** Kategorie eindeutig (z. B. Test, persönlich, unklar) → **nur** [\"Sonstiges\"]. "
            "Sonstiges wird niemals mit anderen Labels kombiniert – bei Sonstiges immer genau ein Label: Sonstiges. "
        )
        label_logic = (
            "Banking=Absender/Inhalt Bank, Konto, Transaktionen (nicht AGB/Cloud). "
            "Streaming=Video/Musik-Anbieter wie Netflix/Spotify/Prime (nicht Fahrdienste). "
            "Rechnung=Inhalt ist Rechnungsstellung, Zahlungsziel, Faktura. "
            "Warnung=Fehlermeldung oder Sicherheitshinweis. "
            "Shopping=Bestellung, Versand, Tracking. "
            "Social Media=Benachrichtigung von LinkedIn/Twitter/Instagram/Facebook/YouTube. "
            "Support=Hilfe, Ticket, Bug, Kundenservice-Dialog. "
            "Newsletter=Massenversand mit Marketing/Update von Anbieter/Marke – nicht: persönliche 1:1-Mail, Test-Mail. "
            "Versicherung=Police, Beitrag, Schaden (nicht Legal/AGB). "
            "Sonstiges=Mail erfüllt keine der obigen Kategorien eindeutig; dann **nur** [\"Sonstiges\"], kein zweites Label."
        )
        closing_rule = (
            " Wenn keine Kategorie eindeutig passt: ausschließlich [\"Sonstiges\"]. Antworte nur mit JSON: {\"labels\":[\"...\"]}."
        )
        system_msg = (
            default_rule
            + "Kategorien: "
            + ", ".join(self.labels_allowed)
            + ". "
            + label_logic
            + closing_rule
        )
        shots = [
            ("From: rechnung@firma.de\nSubject: Ihre Rechnung 2025-09\nBody: Betrag 129,00 EUR, Zahlungsziel 14 Tage.", ["Rechnung"]),
            ("From: shop@beispiel.de\nSubject: Versandbestätigung Bestellung 12345\nBody: Ihr Paket ist unterwegs, Tracking enthalten.", ["Shopping"]),
            ("From: noreply@bank.de\nSubject: Neue Anmeldung erkannt\nBody: Falls Sie das nicht waren, ändern Sie sofort Ihr Passwort.", ["Warnung"]),
            ("From: CloudPlatform-noreply@google.com\nSubject: [Legal Update] Google transitions to data processor for reCAPTCHA\nBody: We're writing to let you know... legal terms... data processor...", ["Sonstiges"]),
            ("From: Bolt\nSubject: Fahre nach deinen Vorstellungen\nBody: Mit der Bolt App... Fahrttypen, Route anpassen, Buchung.", ["Newsletter"]),
            ("From: news@anbieter.de\nSubject: Angebote der Woche\nBody: -20% auf alles, jetzt zugreifen.", ["Newsletter"]),
            ("From: Schwerdhoefer, Sebastian\nSubject: Testmail\nBody: Das ist nur ein Test", ["Sonstiges"]),
            ("From: unknown@random.org\nSubject: Fwd: Meeting\nBody: Unklarer Inhalt, keine klare Kategorie.", ["Sonstiges"]),
        ]
        user_msg = f"From: {sender}\nSubject: {subject}\nBody: {body[:1500]}"
        messages = [{"role": "system", "content": system_msg}]
        for u, labels in shots:
            messages.append({"role": "user", "content": u})
            messages.append({"role": "assistant", "content": json.dumps({"labels": labels}, ensure_ascii=False)})
        messages.append({"role": "user", "content": user_msg})
        return messages

    def _classify_via_ollama(self, sender: str, subject: str, body: str) -> List[str]:
        messages = self._ollama_messages(sender, subject, body)
        base_url = self.ollama_base_url.rstrip("/")
        ollama_format = {
            "type": "object",
            "properties": {
                "labels": {
                    "type": "array",
                    "items": {"type": "string", "enum": self.labels_allowed},
                    "minItems": 1,
                    "maxItems": 3,
                }
            },
            "required": ["labels"],
            "additionalProperties": False,
        }
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "format": ollama_format,
            "options": {"temperature": 0.2},
            "stream": False,
        }
        last_err: Exception | None = None
        txt = ""
        for attempt in range(2):
            try:
                with httpx.Client(timeout=90) as client:
                    r = client.post(f"{base_url}/api/chat", json=payload)
                    r.raise_for_status()
                    data = r.json()
                    txt = (data.get("message") or {}).get("content") or ""
                    break
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    txt = self._ollama_v1_chat(messages, base_url)
                    if txt is not None:
                        break
                    last_err = e
                elif e.response.status_code == 400 and attempt == 0 and payload.get("format") is not None:
                    logger.debug("Ollama format-Schema nicht unterstützt, versuche format: json")
                    payload["format"] = "json"
                    last_err = e
                    continue
                else:
                    last_err = e
                sleep_s = 2 ** attempt
                logger.warning("Ollama-Klassifikation Versuch %d fehlgeschlagen (%s), retry in %ds", attempt + 1, e, sleep_s)
                time.sleep(sleep_s)
            except Exception as e:
                last_err = e
                sleep_s = 2 ** attempt
                logger.warning("Ollama-Klassifikation Versuch %d fehlgeschlagen (%s), retry in %ds", attempt + 1, e, sleep_s)
                time.sleep(sleep_s)
        else:
            logger.error("Ollama-Klassifikation fehlgeschlagen: %s", last_err)
            return ["Sonstiges"]

        parsed = _extract_labels_json(txt)
        if parsed:
            labels = [l for l in parsed.get("labels", []) if l in self.labels_allowed]
            if labels:
                return labels
        return ["Sonstiges"]

    def _ollama_v1_chat(self, messages: list, base_url: str) -> str | None:
        """Ollama-API /v1/chat/completions (Fallback bei 404 von /api/chat)."""
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "temperature": 0.2,
            "stream": False,
        }
        try:
            with httpx.Client(timeout=90) as client:
                r = client.post(f"{base_url}/v1/chat/completions", json=payload)
                r.raise_for_status()
                data = r.json()
                return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        except Exception as e:
            logger.debug("Ollama /v1/chat/completions fehlgeschlagen: %s", e)
            return None
