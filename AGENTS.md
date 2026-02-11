# Gmail Helper – Agent Dokumentation

> Diese Datei enthält wichtige Informationen für AI-Coding-Agenten, die an diesem Projekt arbeiten.

---

## Projekt-Übersicht

**Gmail Helper** ist eine Python-Anwendung zur KI-gestützten automatischen E-Mail-Klassifizierung für Gmail. Die Anwendung analysiert E-Mails lokal mit einer KI (Ollama) und ordnet sie automatisch in vordefinierte Kategorien ein – ohne Cloud, ohne API-Kosten, ohne Datenweitergabe.

### Kernfunktionen

1. Liest neue E-Mails aus dem Gmail-Postfach (z.B. ungelesene der letzten 2 Tage)
2. Analysiert Inhalt mit lokaler KI (Absender, Betreff, Text)
3. Ordnet automatisch Labels aus 10 Kategorien zu
4. Setzt Gmail-Labels automatisch

### Kategorien (Labels)

| Label | Beschreibung |
|-------|--------------|
| Banking | Bank- & Finanzkommunikation |
| Streaming | Video/Musik-Abos |
| Rechnung | Rechnungen & Zahlungsaufforderungen |
| Warnung | Sicherheits- & Fehlermeldungen |
| Shopping | Bestellungen & Versand |
| Social Media | Plattform-Benachrichtigungen |
| Support | Kundenservice & Tickets |
| Newsletter | Marketing & Updates |
| Versicherung | Versicherungs-Dokumente |
| Sonstiges | Alles andere (Fallback) |

---

## Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| Sprache | Python 3.11+ |
| Lokale KI | Ollama (REST API auf Port 11434) |
| KI-Modell | Standard: `mistral:7b-instruct` (~4.4 GB) |
| Alternativen | `qwen2.5:7b-instruct`, `llama3.1:8b`, `qwen2.5:3b` |
| Gmail API | Google API Client (OAuth 2.0) |
| HTTP Client | httpx |
| Konfiguration | python-dotenv |
| UI (optional) | Tkinter |
| CLI | Bash-Script (`gmailhelper`) |

### Python-Abhängigkeiten

```
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
httpx
python-dotenv
```

---

## Projektstruktur

```
gmail-helper/
├── app/                          # Haupt-Python-Paket
│   ├── __init__.py              # Paket-Initialisierung
│   ├── main.py                  # Hauptprogramm, 2-Pass-Verarbeitung
│   ├── classifier.py            # KI-Klassifizierung (Ollama)
│   ├── gmail_client.py          # Gmail API Integration
│   ├── config.py                # Konfigurationsmanagement (AppConfig)
│   ├── utils.py                 # Heuristiken & Hilfsfunktionen
│   └── setup.py                 # Interaktives Setup-Script
├── prompts/
│   └── classification_instructions.md  # KI-Prompt-Kriterien
├── gmailhelper                   # CLI-Entrypoint (Bash)
├── launcher.py                   # Optional: Tkinter UI
├── requirements.txt              # Python-Abhängigkeiten
├── .env.example                  # Beispiel-Konfiguration
├── .gitignore                    # Ignoriert: credentials.json, token.json, .env
├── Dockerfile                    # Container-Build
├── run                           # Universal run helper
└── README.md                     # Benutzer-Dokumentation (Deutsch)
```

---

## Architektur

### 2-Pass-Verarbeitung

Das Hauptprogramm (`app/main.py`) arbeitet in zwei Durchgängen:

**Pass 1: Neue E-Mails klassifizieren**
- Sucht nach ungelesenen E-Mails der letzten 2 Tage
- Klassifiziert mit Ollama-KI
- Setzt Labels in Gmail
- Überspringt bereits spezifisch gelabelte E-Mails

**Pass 2: Re-Labeling für "Sonstiges"**
- Sucht nach E-Mails mit nur "Sonstiges"-Label (neuer als 7 Tage)
- Erneute Klassifizierung (bessere Kontext-Erkennung)
- Entfernt "Sonstiges" wenn spezifische Labels gefunden

### Klassifizierungs-Hierarchie

1. **KI-Klassifizierung** (Ollama) – Primär
2. **Heuristik-Fallback** (`utils.py`) – wenn KI nur "Sonstiges" liefert

Heuristik-Priorität: Rechnung > Warnung > Banking > Support > Newsletter > Social Media > Shopping > Streaming > Versicherung

### Konfigurations-Ladereihenfolge

1. Default-Werte in `AppConfig`
2. `.env`-Datei (via `load_dotenv()`)
3. CLI-Argumente (höchste Priorität)

---

## Entwicklungs-Workflow

### Setup für Entwicklung

```bash
# Repository klonen
cd gmail-helper

# Python Environment erstellen
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Abhängigkeiten installieren
pip install -r requirements.txt
```

### Ausführen

```bash
# Direkt mit Python (für Entwicklung)
python -m app.main --dry-run --max-results 10

# Oder über das CLI-Script
./gmailhelper run --test
./gmailhelper run --live
```

### Wichtige Dateien für Entwicklung

| Datei | Zweck |
|-------|-------|
| `credentials.json` | Gmail OAuth Client Secrets (manuell zu beschaffen) |
| `token.json` | OAuth Access Token (automatisch generiert) |
| `.env` | Lokale Konfiguration (nicht committen!) |

---

## CLI-Befehle

| Befehl | Beschreibung |
|--------|--------------|
| `gmailhelper` | Willkommensbildschirm mit System-Info |
| `gmailhelper setup` | Erstinstallation durchführen |
| `gmailhelper setup --reset` | Einstellungen ändern (Token bleibt) |
| `gmailhelper run --test` | Testlauf (Dry-Run, einmalig) |
| `gmailhelper run --live` | Live-Dauerlauf (alle 30s) |
| `gmailhelper run --test --max-results 50` | Test mit 50 E-Mails |
| `gmailhelper stop` | Alle laufenden Prozesse stoppen |
| `gmailhelper status` | System-Status anzeigen |
| `gmailhelper help` | Detaillierte Hilfe |

---

## Konfiguration

### Umgebungsvariablen (`.env`)

```bash
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b-instruct

# Gmail Query
GMAIL_Q=in:inbox is:unread newer_than:2d
MAX_RESULTS=20

# Verhalten
DRY_RUN=false
SET_LABEL_COLORS=false
LOG_LEVEL=INFO
```

### Programmatische Konfiguration

```python
from app.config import load_config

cfg = load_config()
print(cfg.ollama_model)  # "mistral:7b-instruct"
print(cfg.gmail_query)   # "in:inbox is:unread newer_than:2d"
```

---

## Code-Stil & Konventionen

### Sprache

- **Code-Kommentare**: Deutsch
- **Dokumentation**: Deutsch
- **Variablennamen**: Englisch (Python-Standard)
- **Log-Messages**: Deutsch

### Python-Stil

- Typ-Hints verwenden (`from __future__ import annotations`)
- Dataclasses für Konfiguration (`@dataclass(slots=True)`)
- Logging über `logging.getLogger(__name__)`
- Exception-Handling mit `logger.exception()` für Stacktraces

### Beispiel:

```python
from __future__ import annotations
import logging
from typing import List

logger = logging.getLogger(__name__)

def classify_email(subject: str, sender: str) -> List[str]:
    """Klassifiziert eine E-Mail nach Betreff und Absender."""
    try:
        # Logik hier
        return ["Newsletter"]
    except Exception as exc:
        logger.exception("Fehler bei Klassifikation: %s", exc)
        return ["Sonstiges"]
```

---

## Testing

### Kein formelles Test-Framework

Das Projekt verwendet kein pytest/unittest. Stattdessen:

1. **Dry-Run Modus**: `--dry-run` zeigt Aktionen ohne Ausführung
2. **Test-E-Mails**: Gmail-Query auf kleinen Zeitraum beschränken
3. **Ollama lokal**: API direkt testen via `curl http://localhost:11434/api/tags`

### Manuelle Tests

```bash
# KI-Verbindung testen
curl http://localhost:11434/api/tags

# Gmail API testen (Dry-Run)
python -m app.main --dry-run --max-results 5

# Heuristik testen
python -c "from app.utils import heuristic_labels; print(heuristic_labels('Rechnung', 'shop@test.de', ''))"
```

---

## Sicherheitsaspekte

### Lokale Verarbeitung

- **Keine Cloud-KI**: Ollama läuft lokal, E-Mails verlassen den Rechner nicht
- **Minimaler Gmail-Scope**: Nur `gmail.modify` (Labels setzen/entfernen)
- **Body-Limit**: E-Mail-Text wird auf 1000 Zeichen gekürzt für Analyse

### Sensitive Dateien

Diese Dateien sind in `.gitignore` und dürfen **niemals** committet werden:

- `credentials.json` – OAuth Client Secrets
- `token.json` – OAuth Access Token
- `.env` – Lokale Konfiguration mit potenziell sensiblen Werten

### Token-Handling

- `token.json` wird automatisch bei erstem Lauf erstellt
- Refresh-Token ermöglicht dauerhafte Authentifizierung
- Bei Problemen: `token.json` löschen und neu authentifizieren

---

## Fehlerbehebung

### Häufige Probleme

**"Ollama nicht erreichbar"**
```bash
ollama serve  # Startet Ollama im Vordergrund
```

**"credentials.json nicht gefunden"**
1. Google Cloud Console → APIs & Services → Credentials
2. OAuth 2.0 Client ID erstellen (Desktop App)
3. `credentials.json` herunterladen ins Projektverzeichnis

**Setup zurücksetzen**
```bash
gmailhelper setup --reset  # Token bleibt erhalten
```

---

## Deployment

### Lokale Installation

```bash
gmailhelper setup   # Einmalig ausführen
gmailhelper run --live  # Dauerlauf starten
```

### Docker (experimentell)

```bash
docker build -t gmail-helper .
docker run -v $(pwd)/credentials.json:/app/credentials.json \
           -v $(pwd)/token.json:/app/token.json \
           -v $(pwd)/.env:/app/.env \
           gmail-helper
```

---

## Wichtige Hinweise für Agenten

1. **Sprache beachten**: Dokumentation und Kommentare sind auf Deutsch – neue Code-Kommentare ebenfalls auf Deutsch verfassen.

2. **Keine Breaking Changes am CLI**: Das `gmailhelper`-Script ist der primäre Entrypoint für Benutzer.

3. **Ollama-API**: Die KI-Kommunikation läuft über HTTP (nicht Python-Import). API-Endpunkte:
   - `POST /api/chat` – Haupt-Endpunkt
   - `POST /v1/chat/completions` – Fallback (OpenAI-kompatibel)

4. **Label-Logik**: "Sonstiges" wird **niemals** mit anderen Labels kombiniert. Bei Unsicherheit immer nur `["Sonstiges"]` zurückgeben.

5. **Gmail API Limits**: Batch-Operationen verwenden (`batchModify`), keine Einzel-Requests.

6. **Kategorien sind fest**: Die 10 Labels sind im Code verankert (`ALL_LABELS` in `main.py`, `_HEURISTIC_ALLOWED` in `utils.py`). Änderungen erfordern Updates an mehreren Stellen.
