from __future__ import annotations

import json
import logging
from typing import List

from openai import OpenAI
import httpx
import time

from .utils import extract_text_from_responses, heuristic_labels


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
    """Wrapper um OpenAI Responses API für strukturierte Label-Ausgaben."""

    def __init__(self, api_key: str, model: str, labels_allowed: List[str], provider: str = "openai", ollama_base_url: str | None = None, ollama_model: str | None = None):
        self.provider = provider
        self.model = model
        self.labels_allowed = labels_allowed
        self.ollama_base_url = ollama_base_url or "http://localhost:11434"
        self.ollama_model = ollama_model or "llama3.1"
        self.client = OpenAI(api_key=api_key) if (provider == "openai" and api_key) else None
        self.schema = {
            "name": "email_labels_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "labels": {
                        "type": "array",
                        "items": {"type": "string", "enum": labels_allowed},
                        "minItems": 1,
                        "maxItems": 3,
                    }
                },
                "required": ["labels"],
                "additionalProperties": False,
            },
        }

    def classify(self, sender: str, subject: str, body: str) -> List[str]:
        # 1) KI entscheidet zuerst; Heuristik dient als Fallback
        if self.provider == "ollama":
            ai_labels = self._classify_via_ollama(sender, subject, body)
        else:
            if not self.client:
                logger.warning("OpenAI-Client nicht initialisiert: OPENAI_API_KEY fehlt.")
                ai_labels = ["Sonstiges"]
            else:
                system_msg = (
                    "Du bist ein präziser E‑Mail‑Klassifizierer. Wähle 1–3 Labels aus: "
                    + ", ".join(self.labels_allowed)
                    + ". Wenn nichts passt, nutze 'Sonstiges'. "
                    "Antworte ausschließlich mit JSON im Format {\"labels\":[\"...\"]}. "
                    "Bevorzuge spezifische Labels vor 'Sonstiges'."
                )

                # Few‑Shot Beispiele (4 reichen für Klassifikation, spart Tokens/Kosten)
                shots = [
                    ("From: rechnung@firma.de\nSubject: Ihre Rechnung 2025-09\nBody: Betrag 129,00 EUR, Zahlungsziel 14 Tage.", ["Rechnungen"]),
                    ("From: shop@beispiel.de\nSubject: Versandbestätigung Bestellung 12345\nBody: Ihr Paket ist unterwegs, Tracking enthalten.", ["Shopping"]),
                    ("From: noreply@account.com\nSubject: Neues Konto eingerichtet\nBody: Bitte bestätigen Sie Ihre E‑Mail.", ["Account"]),
                    ("From: news@anbieter.de\nSubject: Angebote der Woche\nBody: -20% auf alles, jetzt zugreifen.", ["Angebote", "Newsletter"]),
                ]

                # Body auf 1500 Zeichen begrenzen (reicht meist; spart API-Kosten)
                user_msg = f"From: {sender}\nSubject: {subject}\nBody: {body[:1500]}"
                messages = [{"role": "system", "content": system_msg}]
                for u, labels in shots:
                    messages.append({"role": "user", "content": u})
                    messages.append({"role": "assistant", "content": json.dumps({"labels": labels}, ensure_ascii=False)})
                messages.append({"role": "user", "content": user_msg})

                try:
                    completion = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        response_format={"type": "json_object"},
                        temperature=0.2,
                    )
                    txt = completion.choices[0].message.content or ""
                except Exception as e:
                    logger.error("Klassifikation (OpenAI) fehlgeschlagen: %s", e)
                    txt = "{}"

                try:
                    data = json.loads(txt)
                    ai_labels = [l for l in data.get("labels", []) if l in self.labels_allowed]
                    if not ai_labels:
                        ai_labels = ["Sonstiges"]
                except Exception:
                    ai_labels = ["Sonstiges"]

        # 2) Fallback/Verstärkung mit Heuristik, wenn KI unentschlossen
        if ai_labels == ["Sonstiges"] or not ai_labels:
            heur = heuristic_labels(subject, sender, body)
            if heur:
                logger.debug("Heuristik-Fallback: %s | %s -> %s", subject[:80], sender, ", ".join(heur))
                return heur
        return ai_labels

    def _ollama_messages(self, sender: str, subject: str, body: str) -> list:
        """Gleiche System- und Few-Shot-Struktur wie OpenAI für bessere lokale Ergebnisse."""
        system_msg = (
            "Du bist ein präziser E‑Mail‑Klassifizierer. Wähle 1–3 Labels aus: "
            + ", ".join(self.labels_allowed)
            + ". Wenn nichts passt, nutze 'Sonstiges'. Antworte ausschließlich mit JSON: {\"labels\":[\"...\"]}. Bevorzuge spezifische Labels."
        )
        shots = [
            ("From: rechnung@firma.de\nSubject: Ihre Rechnung 2025-09\nBody: Betrag 129,00 EUR, Zahlungsziel 14 Tage.", ["Rechnungen"]),
            ("From: shop@beispiel.de\nSubject: Versandbestätigung Bestellung 12345\nBody: Ihr Paket ist unterwegs, Tracking enthalten.", ["Shopping"]),
            ("From: noreply@account.com\nSubject: Neues Konto eingerichtet\nBody: Bitte bestätigen Sie Ihre E‑Mail.", ["Account"]),
            ("From: news@anbieter.de\nSubject: Angebote der Woche\nBody: -20% auf alles, jetzt zugreifen.", ["Angebote", "Newsletter"]),
        ]
        user_msg = f"From: {sender}\nSubject: {subject}\nBody: {body[:1500]}"
        messages = [{"role": "system", "content": system_msg}]
        for u, labels in shots:
            messages.append({"role": "user", "content": u})
            messages.append({"role": "assistant", "content": json.dumps({"labels": labels}, ensure_ascii=False)})
        messages.append({"role": "user", "content": user_msg})
        return messages

    def _classify_via_ollama(self, sender: str, subject: str, body: str) -> List[str]:
        # Native Ollama API mit Structured Output (format = JSON-Schema) für zuverlässigeres JSON
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
            "messages": self._ollama_messages(sender, subject, body),
            "format": ollama_format,
            "options": {"temperature": 0.2},
            "stream": False,
        }
        last_err: Exception | None = None
        txt = ""
        for attempt in range(2):
            try:
                with httpx.Client(timeout=90) as client:
                    r = client.post(f"{self.ollama_base_url}/api/chat", json=payload)
                    r.raise_for_status()
                    data = r.json()
                    txt = (data.get("message") or {}).get("content") or ""
                    break
            except httpx.HTTPStatusError as e:
                # Ältere Ollama-Versionen unterstützen ggf. kein format-Schema; Fallback auf format: "json"
                if e.response.status_code == 400 and attempt == 0 and payload.get("format") is not None:
                    logger.debug("Ollama format-Schema nicht unterstützt, versuche format: json")
                    payload["format"] = "json"
                    last_err = e
                    continue
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


