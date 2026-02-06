from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Tuple


logger = logging.getLogger(__name__)


def extract_text_from_responses(resp: Any) -> str:
    """Extrahiert Textinhalt aus einer OpenAI Responses-Antwort.

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


def heuristic_labels(subject: str, sender: str, body: str) -> List[str]:
    """Einfache, schnelle Vor-Klassifikation auf Basis von Stichwörtern.

    Liefert maximal 3 Labels. Priorität: Rechnungen > Banking > Account > Newsletter
    > Social Media > Support > Arbeit > Privat > Angebote > Streaming >
    Gaming > Klamotten > Technik > Sport > Events > FYI > Sonstiges.
    """
    text = f"{subject}\n{sender}\n{body}".lower()

    def has_any(words: List[str]) -> bool:
        return any(w in text for w in words)

    labels: List[str] = []

    if has_any(["rechnung", "invoice", "faktura", "zahlungsfrist", "beleg", "faktur", "rechnungsnummer", "rechnung von", "invoice from"]):
        labels.append("Rechnungen")
    if has_any(["sparkasse", "volksbank", "commerzbank", "dkb", "n26", "revolut", "konto", "überweisung", "visa", "mastercard"]):
        labels.append("Banking")
    if has_any(["passwort", "password", "2fa", "two-factor", "bestätigungscode", "verification code", "sicherheitswarnung", "kontoaktivität"]):
        labels.append("Account")
    if has_any(["unsubscribe", "abmelden", "newsletter", "newsletter@", "list-unsubscribe", "preferences", "manage subscription"]):
        labels.append("Newsletter")
    if has_any(["linkedin", "instagram", "facebook", "youtube", "tiktok", "twitter", "x.com", "twitch"]):
        labels.append("Social Media")
    if has_any(["hilfe", "support", "problem", "fehler", "bug", "ticket", "störung"]):
        labels.append("Support")
    # Einkaufs-/Bestellbezug eindeutig als Shopping
    if has_any(["bestellung", "auftrag", "lieferung", "track", "sendungsverfolgung", "versandbestätigung", "bestellnummer", "kunde", "kundennummer"]):
        labels.append("Shopping")
    if has_any(["angebot", "sale", "rabatt", "deal", "gutschein", "% rabatt"]):
        labels.append("Angebote")
    if has_any(["netflix", "prime video", "disney+", "spotify", "paramount+"]):
        labels.append("Streaming")
    if has_any(["game", "gaming", "videospiel", "videospiels", "spiel ", "konsole", "steam", "epic games", "xbox", "playstation", "ps5", "ps4", "nintendo", "switch"]):
        labels.append("Gaming")
    if has_any(["mode", "fashion", "klamotten", "retoure", "größe"]):
        labels.append("Klamotten")
    if has_any(["bestellung", "order", "eingegangen", "versandbestätigung", "sendungsverfolgung", "lieferung", "tracking", "bestellnummer", "shop", "kauf", "checkout"]):
        labels.append("Shopping")
    if has_any(["technik", "hardware", "software", "release notes", "firmware", "update"]):
        labels.append("Technik")
    if has_any(["verein", "fitness", "workout", "trainer", "spielplan", "liga"]):
        labels.append("Sport")
    if has_any(["meeting", "projekt", "onboarding", "offboarding", "hr@", "zulieferer", "rechnungstellung", "angebot" ]):
        labels.append("Arbeit")
    if has_any(["termin", "einladung", "webinar", "konferenz", "kalender", "ics "]):
        labels.append("Events")
    if has_any(["zur info", "fyi", "info:", "update:", "status-"]):
        labels.append("FYI")

    # Entdoppeln, Reihenfolge beibehalten
    seen = set()
    result = []
    for l in labels:
        if l not in seen:
            result.append(l)
            seen.add(l)
        if len(result) >= 3:
            break
    return result


