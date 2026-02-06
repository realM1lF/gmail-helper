from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List
import logging

from dotenv import load_dotenv


def _ensure_basic_logging() -> None:
    """Initialisiert ein pragmatisches Logging-Setup, falls noch nicht gesetzt."""
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=os.getenv("LOG_LEVEL", "INFO").upper(),
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )


@dataclass(slots=True)
class AppConfig:
    """Zentralisierte Applikationskonfiguration.

    Werte werden bevorzugt aus Umgebungsvariablen geladen (via .env), mit
    sinnvollen Defaults für lokalen Betrieb.
    """

    openai_api_key: str
    model: str = "gpt-4o-mini"  # günstig & gut für Klassifikation; Alternativen: gpt-4o, gpt-3.5-turbo
    provider: str = "openai"  # openai | ollama
    gmail_query: str = "in:inbox is:unread newer_than:2d"
    labels_allowed: List[str] = field(
        default_factory=lambda: [
            "Rechnungen",
            "Support",
            "Privat",
            "Newsletter",
            "Events",
            "FYI",
            "Banking",
            "Versicherung",
            "Angebote",
            "Streaming",
            "Gaming",
            "Klamotten",
            "Technik",
            "Sport",
            "Arbeit",
            "Shopping",
            "Account",
            "Social Media",
            "Sonstiges",
        ]
    )
    dry_run: bool = False
    max_results: int = 20
    set_label_colors: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"  # Alternativen: llama3.1:8b, mistral:7b-instruct


def load_config(env_file: str | None = None) -> AppConfig:
    """Lädt Konfiguration aus .env/Environment und liefert eine `AppConfig`.

    - Lädt `.env` (falls vorhanden)
    - Liest primäre Parameter für Gmail-Suche, Modell und Limits
    - Aktiviert ein einfaches Logging-Setup
    """

    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    _ensure_basic_logging()

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key:
        logging.getLogger(__name__).warning(
            "OPENAI_API_KEY ist nicht gesetzt. Klassifikation wird fehlschlagen, bis der Key gesetzt ist."
        )

    model = os.getenv("MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    provider = (os.getenv("PROVIDER", "openai").strip() or "openai").lower()
    gmail_query = os.getenv("GMAIL_Q", "in:inbox is:unread newer_than:2d").strip()
    dry_run = os.getenv("DRY_RUN", "false").lower() in {"1", "true", "yes", "y"}
    set_label_colors = os.getenv("SET_LABEL_COLORS", "false").lower() in {"1", "true", "yes", "y"}
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct").strip()

    try:
        max_results = int(os.getenv("MAX_RESULTS", "20"))
    except ValueError:
        max_results = 20

    # Anpassbare Kategorien via ENV (kommasepariert). Fällt zurück auf Default.
    labels_env = os.getenv("LABELS_ALLOWED", "").strip()
    if labels_env:
        labels_allowed = [label.strip() for label in labels_env.split(",") if label.strip()]
    else:
        labels_allowed = [
            "Rechnungen",
            "Support",
            "Privat",
            "Newsletter",
            "Events",
            "FYI",
            "Banking",
            "Versicherung",
            "Angebote",
            "Streaming",
            "Gaming",
            "Klamotten",
            "Technik",
            "Sport",
            "Arbeit",
            "Shopping",
            "Account",
            "Social Media",
            "Sonstiges",
        ]

    return AppConfig(
        openai_api_key=openai_api_key,
        model=model,
        provider=provider,
        gmail_query=gmail_query,
        labels_allowed=labels_allowed,
        dry_run=dry_run,
        max_results=max_results,
        set_label_colors=set_label_colors,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
    )


