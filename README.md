# Gmail Helper

**KI-gestützte automatische E-Mail-Klassifizierung für Gmail**

Gmail Helper analysiert deine E-Mails lokal mit KI (Ollama) und ordnet sie automatisch in Kategorien ein – ohne Cloud, ohne API-Kosten, ohne Datenweitergabe.

```
    ╔═══════════════════════════════════════════════════════════╗
    ║  📧  G M A I L   H E L P E R                              ║
    ╚═══════════════════════════════════════════════════════════╝
```

---

## ✨ Was macht Gmail Helper?

1. **Liest neue E-Mails** aus deinem Gmail-Postfach (z.B. ungelesene der letzten 2 Tage)
2. **Analysiert Inhalt** mit lokaler KI (Absender, Betreff, Text)
3. **Ordnet automatisch Labels zu** aus 10 Kategorien
4. **Setzt Gmail-Labels** – übersichtlich sortiert, ohne manuelles Ablage

### Automatische Kategorien (Labels)

| Label | Beschreibung | Beispiele |
|-------|--------------|-----------|
| **Banking** | Bank- & Finanzkommunikation | Kontoauszüge, Überweisungen, Kartenabbuchungen |
| **Streaming** | Video/Musik-Abos | Netflix, Spotify, Disney+, Prime Video |
| **Rechnung** | Rechnungen & Zahlungsaufforderungen | Rechnungsstellung, Faktura, Zahlungsziel |
| **Warnung** | Sicherheits- & Fehlermeldungen | Login-Warnungen, Verdachtsmeldungen, 2FA |
| **Shopping** | Bestellungen & Versand | Versandbestätigungen, Tracking, Retouren |
| **Social Media** | Plattform-Benachrichtigungen | LinkedIn, Instagram, Facebook, YouTube |
| **Support** | Kundenservice & Tickets | Hilfe-Anfragen, Bug-Reports, Tickets |
| **Newsletter** | Marketing & Updates | Werbe-Mails, Angebote, Produkt-Updates |
| **Versicherung** | Versicherungs-Dokumente | Police, Beitrag, Schadensmeldung |
| **Sonstiges** | Alles andere | Persönliches, Test-Mails, unklare Inhalte |

---

## 🚀 Schnellstart (3 Schritte)

### 1. Repository klonen

```bash
git clone <repository-url>
cd gmail-helper/.gmail-ai
```

### 2. Einmalig Setup ausführen

```bash
gmailhelper setup
```

Das interaktive Setup erledigt alles automatisch:
- ✅ Prüft Systemvoraussetzungen
- ✅ Installiert Ollama (KI-Laufzeit)
- ✅ Lädt KI-Modell herunter (~4.4 GB)
- ✅ Richtet Python-Umgebung ein
- ✅ Konfiguriert Gmail OAuth
- ✅ Erstellt Konfiguration

**Dauer:** ca. 10-15 Minuten (je nach Internet)

### 3. Starten

```bash
# Testlauf (zeigt an, setzt keine Labels)
gmailhelper run --test

# Live-Betrieb (setzt wirklich Labels)
gmailhelper run --live
```

---

## 🖥️ Systemanforderungen

| | Minimal | Empfohlen |
|--|---------|-----------|
| **RAM** | 8 GB | 16 GB |
| **Speicher** | 10 GB frei | 15 GB frei |
| **Betriebssystem** | macOS 12+, Ubuntu 20.04+ | macOS 14+, Ubuntu 22.04+ |
| **Internet** | Erforderlich für Setup | Erforderlich für Setup |
| **Browser** | Für Gmail OAuth | Für Gmail OAuth |

**Hinweis:** Windows wird aktuell nicht unterstützt.

---

## 📋 Alle Befehle

| Befehl | Beschreibung |
|--------|--------------|
| `gmailhelper` | Zeigt Willkommensbildschirm mit System-Info |
| `gmailhelper setup` | Erstinstallation durchführen |
| `gmailhelper setup --reset` | Einstellungen ändern (Token bleibt erhalten) |
| `gmailhelper run --test` | Testlauf (Dry-Run, einmalig) |
| `gmailhelper run --live` | Live-Dauerlauf (alle 30s, setzt Labels) |
| `gmailhelper run --test --max-results 50` | Test mit 50 E-Mails |
| `gmailhelper stop` | Alle laufenden Prozesse stoppen |
| `gmailhelper status` | System-Status anzeigen |
| `gmailhelper help` | Detaillierte Hilfe |

---

## ⚙️ Konfiguration

Die Konfiguration wird in `.env` gespeichert:

```bash
# Ollama (lokale KI)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b-instruct

# Gmail Query (welche E-Mails bearbeiten)
GMAIL_Q=in:inbox is:unread newer_than:2d

# Verhalten
MAX_RESULTS=20
DRY_RUN=false
SET_LABEL_COLORS=false
LOG_LEVEL=INFO
```

**Anpassen:**
```bash
# Eigene Gmail-Suchanfrage
gmailhelper run --test --q "in:inbox newer_than:1d"

# Mehr E-Mails auf einmal
gmailhelper run --test --max-results 50
```

---

## 🔒 Datenschutz & Sicherheit

- **🔐 Lokale KI:** Keine Daten gehen in die Cloud (Ollama läuft lokal)
- **📧 Nur Gmail-Scope:** `gmail.modify` (Labels setzen/entfernen)
- **🚫 Keine Datenweitergabe:** E-Mails werden nur lokal analysiert
- **⚠️ Sensible Dateien:** `.env`, `credentials.json`, `token.json` sind in `.gitignore`
- **📝 Body-Limit:** E-Mail-Text wird auf 1000 Zeichen gekürzt für Analyse

---

## 🐛 Fehlerbehebung

### "Ollama nicht erreichbar"
```bash
# Ollama manuell starten
ollama serve
```

### "credentials.json nicht gefunden"
1. Gehe zu [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Erstelle OAuth 2.0 Client ID (Desktop App)
3. Lade `credentials.json` herunter
4. Kopiere es ins Projektverzeichnis

### Setup neu starten
```bash
# Einstellungen ändern (Token & Credentials bleiben)
gmailhelper setup --reset
```

### Prozesse stoppen
```bash
gmailhelper stop
```

---

## 🏗️ Architektur

```
gmail-helper/
├── app/
│   ├── main.py          # Hauptprogramm, 2-Pass-Verarbeitung
│   ├── classifier.py    # KI-Klassifizierung (Ollama)
│   ├── gmail_client.py  # Gmail API Integration
│   ├── config.py        # Konfigurationsmanagement
│   ├── utils.py         # Heuristiken & Hilfsfunktionen
│   └── setup.py         # Interaktives Setup
├── gmailhelper           # CLI-Entrypoint
├── requirements.txt      # Python-Abhängigkeiten
└── README.md            # Diese Datei
```

**2-Pass-Verarbeitung:**
1. **Pass 1:** Neue ungelesene E-Mails klassifizieren & labeln
2. **Pass 2:** E-Mails mit nur "Sonstiges" nach 7 Tagen erneut prüfen

---

## 🤝 Mitmachen

Fehler gefunden oder Feature-Wunsch? Erstelle ein Issue oder Pull Request!

---

## 📄 Lizenz

MIT License – Siehe [LICENSE](LICENSE)

---

**Made with ❤️ für übersichtliche Postfächer**
