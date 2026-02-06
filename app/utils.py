from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Tuple


logger = logging.getLogger(__name__)


def extract_text_from_responses(resp: Any) -> str:
    """Extrahiert Textinhalt aus einer Responses-Antwort (legacy/optional).

    Bevorzugt `resp.output_text` (neuere SDKs). Fällt konservativ auf bekannte
    Strukturen zurück, falls das Feld nicht existiert.
    """

    text = getattr(resp, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text

    # Fallback: häufige Struktur in Responses
    try:
        outputs = getattr(resp, "output", None) or []
        if outputs and getattr(outputs[0], "content", None):
            maybe = outputs[0].content[0]
            return getattr(maybe, "text", "") or (maybe.get("text", "") if isinstance(maybe, dict) else "")
    except Exception as exc:  # pragma: no cover - defensiv
        logger.debug("Konnte Text aus Response nicht extrahieren: %s", exc)

    return ""


def safe_json(text: str, default: Dict[str, Any]) -> Dict[str, Any]:
    """Parst JSON sicher und liefert bei Fehlern `default`."""
    try:
        return json.loads(text)
    except Exception:
        return default


# Nur diese Labels dürfen von der Heuristik zurückgegeben werden (wie in main.ALL_LABELS).
_HEURISTIC_ALLOWED = frozenset({
    "Banking", "Streaming", "Rechnung", "Warnung", "Shopping",
    "Social Media", "Support", "Newsletter", "Versicherung",
})


def heuristic_labels(subject: str, sender: str, body: str) -> List[str]:
    """Einfache Klassifikation per Stichwörter. Nur erlaubte Labels (kein Sonstiges).

    Priorität: Rechnung > Warnung > Banking > Support > Newsletter > Social Media
    > Shopping > Streaming > Versicherung. Maximal 3 Labels.
    """
    text = f"{subject}\n{sender}\n{body}".lower()

    def has_any(words: List[str]) -> bool:
        return any(w in text for w in words)

    labels: List[str] = []

    if has_any(["rechnung", "invoice", "faktura", "zahlungsfrist", "beleg", "faktur", "rechnungsnummer", "rechnung von", "invoice from"]):
        labels.append("Rechnung")
    if has_any(["passwort", "password", "2fa", "two-factor", "bestätigungscode", "verification code", "sicherheitswarnung", "kontoaktivität", "fehlermeldung", "fehler beim", "warnung:", "verdächtig"]):
        labels.append("Warnung")
    if has_any(["sparkasse", "volksbank", "commerzbank", "dkb", "n26", "revolut", "konto", "überweisung", "visa", "mastercard"]):
        labels.append("Banking")
    if has_any(["hilfe", "support", "problem", "fehler", "bug", "ticket", "störung"]):
        labels.append("Support")
    if has_any(["unsubscribe", "abmelden", "newsletter", "newsletter@", "list-unsubscribe", "preferences", "manage subscription"]):
        labels.append("Newsletter")
    if has_any(["linkedin", "instagram", "facebook", "youtube", "tiktok", "twitter", "x.com", "twitch"]):
        labels.append("Social Media")
    if has_any(["bestellung", "auftrag", "lieferung", "track", "sendungsverfolgung", "versandbestätigung", "bestellnummer", "order", "tracking", "shop", "kauf", "checkout"]):
        labels.append("Shopping")
    if has_any(["netflix", "prime video", "disney+", "spotify", "paramount+"]):
        labels.append("Streaming")
    if has_any(["versicherung", "police", "beitrag", "schaden", "schadensmeldung"]):
        labels.append("Versicherung")

    # Nur erlaubte Labels, entdoppelt, max 3
    seen = set()
    result = []
    for l in labels:
        if l in _HEURISTIC_ALLOWED and l not in seen:
            result.append(l)
            seen.add(l)
        if len(result) >= 3:
            break
    return result


