# Gmail Helper (Gmail AI Labeler)

**Gmail Helper** ist ein kleines Python-Tool, das deine Gmail-Postfächer automatisch ordnet: Es holt neue E-Mails ab, klassifiziert sie per KI in vordefinierte Kategorien und setzt die passenden Gmail-Labels. So bleiben Rechnungen, Newsletter, Support und Co. übersichtlich sortiert – ohne manuelles Ablage.

## Was macht das Projekt?

- **E-Mails abrufen:** Nutzt die Gmail API und eine konfigurierbare Suchanfrage (z. B. ungelesen, letzte 2 Tage).
- **Klassifizieren:** Jede Nachricht wird an ein Sprachmodell geschickt (Absender, Betreff, Anriss des Bodys). Das Modell wählt 1–3 Labels aus einer festen Liste (z. B. Rechnungen, Support, Newsletter, Banking, Shopping).
- **Labels setzen:** Die gewählten Gmail-Labels werden den Nachrichten zugewiesen. Bereits spezifisch gelabelte Mails werden übersprungen.
- **Re-Labeling:** E-Mails, die nur „Sonstiges“ haben, werden in einem zweiten Durchlauf erneut geprüft (z. B. innerhalb der letzten 7 Tage), um nachträglich passendere Labels zu vergeben.

Unterstützt werden **OpenAI** (z. B. gpt-4o-mini, gpt-4o) und **Ollama** (lokal, ohne API-Kosten).

## Voraussetzungen

- Python 3.11+
- Gmail-Konto mit OAuth 2.0 (Desktop Client): `credentials.json`
- Optional: OpenAI API-Key **oder** lokale Ollama-Instanz

## Schnellstart

1. **Repository klonen und Abhängigkeiten installieren**

   ```bash
   cd .gmail-ai
   pip install -r requirements.txt
   ```

2. **Umgebung konfigurieren**

   - `.env` anlegen (orientiere dich an `.env.example`).
   - **OpenAI:** `OPENAI_API_KEY` setzen, optional `MODEL=gpt-4o-mini`.
   - **Ollama (lokal):** `PROVIDER=ollama` setzen, optional `OLLAMA_MODEL=qwen2.5:7b-instruct`.

3. **Gmail OAuth einrichten**

   - `credentials.json` (OAuth Desktop Client von Google Cloud Console) ins Projektverzeichnis legen.
   - Ersten Lauf ausführen (öffnet Browser für Anmeldung, erzeugt `token.json`):

   ```bash
   python app/main.py --dry-run
   ```

4. **Dry-Run vs. echte Änderungen**

   - Nur anzeigen, was gelabelt würde:  
     `python app/main.py --dry-run`
   - Labels tatsächlich setzen:  
     `python app/main.py`

## Nutzung

| Aktion              | Befehl |
|---------------------|--------|
| Dry-Run (nur anzeigen) | `python app/main.py --dry-run` |
| Labels setzen       | `python app/main.py` |
| Eigene Gmail-Query  | `python app/main.py --q "in:inbox newer_than:7d"` |
| Max. Anzahl Mails    | `python app/main.py --max-results 50` |
| Dauerlauf (Intervall) | `python app/main.py --loop --interval 60` |

## Konfiguration (Umgebungsvariablen)

| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `OPENAI_API_KEY` | API-Key für OpenAI (bei `PROVIDER=openai`) | – |
| `MODEL` | OpenAI-Modell | `gpt-4o-mini` |
| `PROVIDER` | `openai` oder `ollama` | `openai` |
| `OLLAMA_BASE_URL` | Basis-URL der Ollama-Instanz | `http://localhost:11434` |
| `OLLAMA_MODEL` | Modellname bei Ollama | `qwen2.5:7b-instruct` |
| `GMAIL_Q` | Gmail-Suchanfrage | `in:inbox is:unread newer_than:2d` |
| `MAX_RESULTS` | Max. Anzahl zu bearbeitender Mails pro Lauf | `20` |
| `DRY_RUN` | Nur planen, keine Labels setzen | `false` |
| `SET_LABEL_COLORS` | Gmail-Label-Farben setzen | `false` |
| `LOG_LEVEL` | Logging (z. B. DEBUG, INFO) | `INFO` |

Weitere Optionen siehe `app/config.py` und `.env.example`.

## Modell & Kosten

- **OpenAI:** Standard ist `gpt-4o-mini` (günstig, für Klassifikation geeignet). Über `MODEL` z. B. `gpt-4o` oder `gpt-3.5-turbo` wählbar.
- **Ollama (lokal):** Mit `PROVIDER=ollama` wird die lokale Ollama-Instanz genutzt (keine API-Kosten). Empfohlene Modelle für stabiles JSON und deutsche Mails:
  - `qwen2.5:7b-instruct`
  - `llama3.1:8b`, `mistral:7b-instruct`
  - Leichtgewichte: `qwen2.5:3b`

## Docker & ddev

- **Docker-Image bauen** (im Projektordner `.gmail-ai`):

  ```bash
  docker build -t gmail-ai:local .
  ```

- **ddev:** Über `.ddev/docker-compose.gmail.yaml` können zusätzliche Services (z. B. Ollama) eingebunden werden. `credentials.json` und `token.json` per Volume mounten.

  ```bash
  ddev start
  ddev exec -s gmailai python app/main.py --dry-run
  ```

## Sicherheit & sensible Daten

- **Nur notwendiger Gmail-Scope:** `gmail.modify` (Labels setzen/entfernen).
- **Keine sensiblen Dateien ins Repository:**  
  `.env`, `credentials.json` und `token.json` stehen in `.gitignore` und dürfen **niemals** eingecheckt werden.
- **Body-Länge:** E-Mail-Body wird für die KI auf einen begrenzten Anriss (z. B. 1500 Zeichen) gekürzt.

## Projektstruktur (Auszug)

```
.gmail-ai/
├── app/
│   ├── main.py          # Einstieg, Ablauf (Labels holen → klassifizieren → setzen)
│   ├── classifier.py    # KI-Anbindung (OpenAI + Ollama), strukturierte Label-Ausgabe
│   ├── gmail_client.py  # Gmail API (Labels, Nachrichten lesen/schreiben)
│   ├── config.py        # Konfiguration aus Umgebungsvariablen
│   └── utils.py         # Heuristiken, JSON-Hilfen
├── prompts/
│   └── classification_instructions.md  # Regeln/Beispiele für die Klassifikation
├── requirements.txt
├── Dockerfile
├── .env.example         # Vorlage für .env (ohne echte Secrets)
└── README.md
```

## Lizenz

MIT
