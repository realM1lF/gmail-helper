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
    sinnvollen Defaults für lokalen Betrieb. KI-Klassifikation läuft über Ollama.
    """

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct"
    gmail_query: str = "in:inbox is:unread newer_than:2d"
    labels_allowed: List[str] = field(
        default_factory=lambda: [
            "Banking",
            "Streaming",
            "Rechnung",
            "Warnung",
            "Shopping",
            "Social Media",
            "Support",
            "Newsletter",
            "Versicherung",
            "Sonstiges",
        ]
    )
    dry_run: bool = False
    max_results: int = 20
    set_label_colors: bool = False


def load_config(env_file: str | None = None) -> AppConfig:
    """Lädt Konfiguration aus .env/Environment und liefert eine `AppConfig`."""

    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    _ensure_basic_logging()

    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    ollama_model = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct").strip()
    gmail_query = os.getenv("GMAIL_Q", "in:inbox is:unread newer_than:2d").strip()
    dry_run = os.getenv("DRY_RUN", "false").lower() in {"1", "true", "yes", "y"}
    set_label_colors = os.getenv("SET_LABEL_COLORS", "false").lower() in {"1", "true", "yes", "y"}

    try:
        max_results = int(os.getenv("MAX_RESULTS", "20"))
    except ValueError:
        max_results = 20

    labels_env = os.getenv("LABELS_ALLOWED", "").strip()
    if labels_env:
        labels_allowed = [label.strip() for label in labels_env.split(",") if label.strip()]
    else:
        labels_allowed = [
            "Banking",
            "Streaming",
            "Rechnung",
            "Warnung",
            "Shopping",
            "Social Media",
            "Support",
            "Newsletter",
            "Versicherung",
            "Sonstiges",
        ]

    return AppConfig(
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        gmail_query=gmail_query,
        labels_allowed=labels_allowed,
        dry_run=dry_run,
        max_results=max_results,
        set_label_colors=set_label_colors,
    )
