#!/usr/bin/env python3
"""
Gmail Helper Setup - Interaktives Setup-Script
Usage: gmailhelper setup [--reset]
"""
from __future__ import annotations

import os
import sys
import json
import subprocess
import platform
import time
import argparse
from pathlib import Path
from typing import Optional

# Farbcodes
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
MAGENTA = "\033[0;35m"
NC = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_PATH = PROJECT_ROOT / ".venv"
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"
TOKEN_PATH = PROJECT_ROOT / "token.json"
ENV_PATH = PROJECT_ROOT / ".env"
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"


def print_header(text: str) -> None:
    """Gefärbte Header-Ausgabe"""
    print(f"\n{BOLD}{BLUE}[{text}]{NC}")


def print_success(text: str) -> None:
    print(f"   {GREEN}✅ {text}{NC}")


def print_warning(text: str) -> None:
    print(f"   {YELLOW}⚠️  {text}{NC}")


def print_error(text: str) -> None:
    print(f"   {RED}❌ {text}{NC}")


def print_info(text: str) -> None:
    print(f"   {CYAN}ℹ️  {text}{NC}")


def print_step(step_num: int, total: int, title: str) -> None:
    """Schritt-Header"""
    print(f"\n{BOLD}{MAGENTA}[{step_num}/{total}] {title}{NC}")


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    """Ja/Nein Abfrage"""
    suffix = " [J/n]: " if default else " [j/N]: "
    while True:
        response = input(f"   {prompt}{suffix}").strip().lower()
        if not response:
            return default
        if response in ("j", "ja", "y", "yes"):
            return True
        if response in ("n", "nein", "no"):
            return False
        print("   Bitte 'j' oder 'n' eingeben")


def ask_keep_or_reset(what: str, current_value: str = "") -> bool:
    """Frage ob bestehenden Wert behalten oder neu konfigurieren"""
    if current_value:
        print_info(f"Aktuell: {current_value}")
    return ask_yes_no(f"{what} behalten?", default=True)


def run_command(cmd: list[str], cwd: Optional[Path] = None, check: bool = False) -> tuple[int, str, str]:
    """Befehl ausführen und Output zurückgeben"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def check_system() -> bool:
    """System-Check durchführen"""
    # OS erkennen
    system = platform.system()
    if system == "Darwin":
        print_success(f"macOS {platform.mac_ver()[0]} erkannt")
    elif system == "Linux":
        print_success(f"Linux erkannt ({platform.release()})")
    else:
        print_error(f"Nicht unterstütztes Betriebssystem: {system}")
        return False
    
    # Python Version
    py_version = sys.version_info
    if py_version >= (3, 11):
        print_success(f"Python {py_version.major}.{py_version.minor}.{py_version.micro} gefunden")
    else:
        print_error(f"Python 3.11+ erforderlich, gefunden: {py_version.major}.{py_version.minor}")
        return False
    
    # pip prüfen
    returncode, _, _ = run_command([sys.executable, "-m", "pip", "--version"])
    if returncode == 0:
        print_success("pip verfügbar")
    else:
        print_error("pip nicht gefunden")
        return False
    
    return True


def check_ollama() -> tuple[bool, bool]:
    """Prüft ob Ollama installiert und läuft"""
    installed = False
    running = False
    
    # Prüfe Installation
    returncode, _, _ = run_command(["which", "ollama"])
    if returncode == 0:
        installed = True
    
    # Prüfe ob läuft
    if installed:
        returncode, _, _ = run_command(["curl", "-s", "http://localhost:11434/api/tags"])
        if returncode == 0:
            running = True
    
    return installed, running


def install_ollama() -> bool:
    """Ollama installieren (cross-platform)"""
    system = platform.system()
    
    print_info("Starte Installation...")
    
    if system == "Darwin":
        # macOS - versuche Homebrew
        returncode, _, _ = run_command(["which", "brew"])
        if returncode == 0:
            print_info("Installiere via Homebrew...")
            returncode, stdout, stderr = run_command(["brew", "install", "ollama"], check=True)
            if returncode == 0:
                print_success("Ollama via Homebrew installiert")
                return True
            else:
                print_warning(f"Homebrew Installation fehlgeschlagen: {stderr}")
        
        # Fallback: Curl-Installer
        print_info("Verwende offiziellen Installer...")
        returncode, stdout, stderr = run_command([
            "bash", "-c", 
            'curl -fsSL https://ollama.com/install.sh | sh'
        ])
        if returncode == 0:
            print_success("Ollama installiert")
            return True
        else:
            print_error(f"Installation fehlgeschlagen: {stderr}")
            return False
            
    elif system == "Linux":
        # Linux: Curl-Installer
        print_info("Verwende offiziellen Installer...")
        returncode, stdout, stderr = run_command([
            "bash", "-c",
            'curl -fsSL https://ollama.com/install.sh | sh'
        ])
        if returncode == 0:
            print_success("Ollama installiert")
            return True
        else:
            print_error(f"Installation fehlgeschlagen: {stderr}")
            return False
    
    return False


def start_ollama() -> bool:
    """Ollama Service starten"""
    print_info("Starte Ollama Service...")
    
    # Starte im Hintergrund
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    
    # Warte auf Start
    for i in range(10):
        time.sleep(1)
        returncode, _, _ = run_command(["curl", "-s", "http://localhost:11434/api/tags"])
        if returncode == 0:
            print_success("Ollama läuft")
            return True
        print(f"   Warte auf Ollama... {i+1}/10")
    
    print_error("Ollama konnte nicht gestartet werden")
    return False


def setup_ollama(skip_if_ok: bool = False) -> bool:
    """Ollama Setup durchführen"""
    installed, running = check_ollama()
    
    if installed and running:
        # Version prüfen
        returncode, stdout, _ = run_command(["ollama", "--version"])
        if returncode == 0:
            version = stdout.strip() or "unbekannt"
            print_success(f"Ollama installiert und läuft ({version})")
        else:
            print_success("Ollama installiert und läuft")
        
        if skip_if_ok:
            return True
        
        # Frage ob neu konfigurieren
        if ask_keep_or_reset("Ollama-Installation", "Installiert & läuft"):
            return True
        # User will neu konfigurieren - fahre fort
        
    elif installed and not running:
        print_warning("Ollama installiert, aber nicht gestartet")
        if ask_yes_no("Soll ich Ollama jetzt starten?"):
            return start_ollama()
        return False
    
    # Nicht installiert oder User will neu installieren
    if not installed:
        print_warning("Ollama nicht gefunden")
        print_info("Ollama ist eine lokale KI-Laufzeitumgebung")
        print_info("Mehr Infos: https://ollama.com")
        
        if not ask_yes_no("Soll ich Ollama jetzt installieren?"):
            print_error("Ollama wird für Gmail Helper benötigt")
            print_info("Installiere manuell: curl -fsSL https://ollama.com/install.sh | sh")
            return False
    
    if install_ollama():
        return start_ollama()
    return False


def setup_python_env(skip_if_ok: bool = False) -> bool:
    """Python Environment einrichten"""
    # Prüfe ob venv existiert
    python_exe = VENV_PATH / "bin" / "python" if platform.system() != "Windows" else VENV_PATH / "Scripts" / "python.exe"
    
    if python_exe.exists():
        print_success("Virtual Environment existiert")
        if skip_if_ok:
            return True
        if ask_keep_or_reset("Python Environment", f"Venv bei {VENV_PATH}"):
            return True
        # User will neu - lösche altes venv
        print_info("Lösche altes Virtual Environment...")
        import shutil
        shutil.rmtree(VENV_PATH)
    
    print_info("Erstelle Python Virtual Environment...")
    returncode, _, stderr = run_command([sys.executable, "-m", "venv", str(VENV_PATH)])
    if returncode != 0:
        print_error(f"Konnte venv nicht erstellen: {stderr}")
        return False
    print_success("Virtual Environment erstellt")
    
    # Installiere Abhängigkeiten
    print_info("Installiere Abhängigkeiten...")
    pip_cmd = str(VENV_PATH / "bin" / "pip")
    returncode, _, stderr = run_command([pip_cmd, "install", "-r", "requirements.txt"])
    if returncode != 0:
        print_error(f"Installation fehlgeschlagen: {stderr}")
        return False
    
    print_success("Abhängigkeiten installiert")
    return True


def model_exists(model: str) -> bool:
    """Prüft ob ein Modell in Ollama existiert (verschiedene Methoden)"""
    # Methode 1: ollama show
    returncode, _, _ = run_command(["ollama", "show", model])
    if returncode == 0:
        return True
    
    # Methode 2: ollama list parsen
    returncode, stdout, _ = run_command(["ollama", "list"])
    if returncode == 0:
        # Extrahiere Modellnamen (erste Spalte)
        for line in stdout.split("\n")[1:]:  # Überspringe Header
            parts = line.split()
            if parts:
                installed_model = parts[0].strip()
                # Prüfe exakter Match oder Modellname ohne Tag
                if installed_model == model:
                    return True
                # Prüfe ob Basis-Modellname übereinstimmt
                if ":" in model and installed_model == model.split(":")[0]:
                    return True
    
    return False


def get_installed_models() -> list[str]:
    """Gibt Liste der installierten Modelle zurück"""
    returncode, stdout, _ = run_command(["ollama", "list"])
    models = []
    if returncode == 0:
        for line in stdout.split("\n")[1:]:  # Überspringe Header
            parts = line.split()
            if parts:
                models.append(parts[0].strip())
    return models


def download_model(model: str = "mistral:7b-instruct", skip_if_ok: bool = False) -> bool:
    """KI-Modell herunterladen"""
    print_info(f"Gewünschtes Modell: {model}")
    
    # Prüfe ob das gewünschte Modell schon existiert
    if model_exists(model):
        print_success(f"Modell {model} bereits vorhanden")
        if skip_if_ok:
            return True
        if ask_keep_or_reset("Dieses Modell", model):
            return True
        # User will anderes Modell
        new_model = input(f"   Neues Modell [Enter = {model}]: ").strip()
        if new_model and new_model != model:
            return download_model(new_model, skip_if_ok=False)
        return True
    
    # Modell nicht gefunden - prüfe ob andere Modelle installiert sind
    installed = get_installed_models()
    if installed:
        print_warning(f"Standard-Modell '{model}' nicht installiert")
        print_info("Bereits installierte Modelle:")
        for m in installed:
            print(f"   • {m}")
        print()
        
        # Wenn nur ein Modell installiert ist, verwende das automatisch
        if len(installed) == 1:
            existing = installed[0]
            print_info(f"Verwende vorhandenes Modell: {existing}")
            os.environ["_SETUP_RECOMMENDED_MODEL"] = existing
            return True
        
        # Mehrere Modelle - frage welches verwendet werden soll
        print(f"   {BOLD}Verfügbare Modelle:{NC}")
        for i, m in enumerate(installed, 1):
            print(f"   {i}. {m}")
        print(f"   {len(installed)+1}. Neues Modell herunterladen ({model})")
        
        choice = input(f"   Welches Modell verwenden? [1-{len(installed)+1}]: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(installed):
                selected = installed[idx]
                print_info(f"Verwende {selected}")
                os.environ["_SETUP_RECOMMENDED_MODEL"] = selected
                return True
            elif idx == len(installed):
                # User will neues Modell laden
                new_model = input(f"   Welches Modell laden [Enter = {model}]: ").strip()
                if new_model and new_model != model:
                    return download_model(new_model, skip_if_ok=False)
                # Lade Standard-Modell
            else:
                print_error("Ungültige Auswahl")
                return False
        except ValueError:
            print_error("Ungültige Eingabe")
            return False
    
    # Kein Modell installiert, muss heruntergeladen werden
    print_info(f"Modell '{model}' wird heruntergeladen...")
    print_info("Größe: ca. 4-5 GB | Dauer: 5-10 Minuten")
    
    # Lade Modell herunter
    print()
    print(f"   {CYAN}📥 Download läuft...{NC}")
    print(f"   {DIM}(Zum Abbrechen: Ctrl+C){NC}")
    print(f"   {DIM}Das kann 5-10 Minuten dauern je nach Internetverbindung...{NC}")
    print()
    
    # Verwende ollama pull mit Fortschrittsanzeige
    process = subprocess.Popen(
        ["ollama", "pull", model],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=PROJECT_ROOT
    )
    
    # Zeige Output
    for line in process.stdout:
        line = line.strip()
        if line:
            print(f"      {line}")
    
    process.wait()
    
    if process.returncode == 0:
        print_success(f"Modell {model} bereit")
        return True
    else:
        print_error(f"Download fehlgeschlagen (Code: {process.returncode})")
        return False


def setup_gmail_oauth(skip_if_ok: bool = False) -> bool:
    """Gmail OAuth Setup"""
    has_credentials = CREDENTIALS_PATH.exists()
    has_token = TOKEN_PATH.exists()
    
    if has_credentials and has_token:
        print_success("credentials.json vorhanden")
        print_success("Bereits authentifiziert")
        
        if skip_if_ok:
            return True
        
        # Frage ob neu authentifizieren
        if ask_keep_or_reset("Gmail-Authentifizierung", "Bereits eingerichtet"):
            return True
        # User will neu - Token löschen (nicht credentials!)
        print_info("Lösche bestehenden Token für Neuanmeldung...")
        TOKEN_PATH.unlink(missing_ok=True)
        has_token = False
    
    elif has_credentials and not has_token:
        print_success("credentials.json vorhanden")
        print_warning("Noch nicht authentifiziert")
        if not ask_yes_no("Jetzt bei Google anmelden?", default=True):
            return False
    
    else:
        # Keine credentials
        print_warning("credentials.json nicht gefunden")
        print()
        print(f"   {BOLD}Anleitung für Google Cloud Console:{NC}")
        print()
        print("   1. Öffne: https://console.cloud.google.com")
        print("   2. Erstelle ein neues Projekt (z.B. 'Gmail Helper')")
        print("   3. Aktiviere die Gmail API:")
        print("      - Gehe zu 'APIs & Services' > 'Library'")
        print("      - Suche 'Gmail API' und aktiviere sie")
        print("   4. Erstelle OAuth Credentials:")
        print("      - Gehe zu 'APIs & Services' > 'Credentials'")
        print("      - 'Create Credentials' > 'OAuth client ID'")
        print("      - Application type: 'Desktop app'")
        print("      - Name: 'Gmail Helper Desktop'")
        print("      - 'Create'")
        print("   5. Lade die JSON herunter (credentials.json)")
        print(f"   6. Kopiere sie nach: {PROJECT_ROOT}")
        print()
        print(f"   {CYAN}Direktlink:{NC}")
        print("   https://console.cloud.google.com/apis/credentials")
        print()
        
        if not ask_yes_no("Hast du credentials.json heruntergeladen und in das Projektverzeichnis kopiert?"):
            print_error("Setup kann nicht fortgesetzt werden ohne credentials.json")
            return False
        
        if not CREDENTIALS_PATH.exists():
            print_error("credentials.json wurde nicht gefunden")
            print_info(f"Erwartet bei: {CREDENTIALS_PATH}")
            return False
        
        print_success("credentials.json gefunden")
    
    # Erstelle Token (Erstauthentifizierung)
    print_info("Erstauthentifizierung bei Google...")
    print_info("Ein Browser-Fenster wird geöffnet...")
    print()
    
    # Führe einen Testlauf durch der das Token erstellt
    python_exe = VENV_PATH / "bin" / "python"
    returncode, stdout, stderr = run_command(
        [str(python_exe), "-m", "app.main", "--dry-run", "--max-results", "1"],
        timeout=120
    )
    
    if TOKEN_PATH.exists():
        print_success("Authentifizierung erfolgreich")
        return True
    else:
        print_error("Authentifizierung fehlgeschlagen")
        if stderr:
            print_info(f"Fehler: {stderr}")
        return False


def setup_config(skip_if_ok: bool = False) -> bool:
    """.env Konfiguration erstellen"""
    config = {}
    
    # Lade bestehende .env falls vorhanden
    if ENV_PATH.exists():
        print_info("Bestehende .env gefunden")
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
        
        if skip_if_ok:
            return True
        
        if ask_keep_or_reset("Bestehende Konfiguration", f"{len(config)} Werte"):
            return True
        # User will neu konfigurieren
    
    # Prüfe ob ein Modell im Setup ausgewählt wurde
    recommended_model = os.environ.get("_SETUP_RECOMMENDED_MODEL", "")
    
    # Default-Werte
    default_model = recommended_model if recommended_model else "mistral:7b-instruct"
    defaults = {
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": default_model,
        "GMAIL_Q": "in:inbox is:unread newer_than:2d",
        "MAX_RESULTS": "20",
        "DRY_RUN": "false",
        "SET_LABEL_COLORS": "false",
        "LOG_LEVEL": "INFO",
    }
    
    # Merge mit bestehenden Werten
    for key, default_val in defaults.items():
        if key not in config:
            config[key] = default_val
    
    # Hinweis wenn wir das vorhandene Modell empfehlen
    if recommended_model:
        print_info(f"Verfügbares Modell erkannt: {recommended_model}")
    
    print()
    print(f"   {BOLD}Konfiguration:{NC}")
    print(f"   {DIM}(Enter drücken um aktuellen Wert zu behalten){NC}")
    print()
    
    # Ollama URL
    current = config.get("OLLAMA_BASE_URL", "http://localhost:11434")
    url = input(f"   Ollama URL [{current}]: ").strip()
    config["OLLAMA_BASE_URL"] = url or current
    
    # Modell
    current = config.get("OLLAMA_MODEL", "mistral:7b-instruct")
    model = input(f"   Modell [{current}]: ").strip()
    config["OLLAMA_MODEL"] = model or current
    
    # Gmail Query
    current = config.get("GMAIL_Q", "in:inbox is:unread newer_than:2d")
    query = input(f"   Gmail Query [{current}]: ").strip()
    config["GMAIL_Q"] = query or current
    
    # Max Results
    current = config.get("MAX_RESULTS", "20")
    max_results = input(f"   Max. E-Mails pro Lauf [{current}]: ").strip()
    config["MAX_RESULTS"] = max_results or current
    
    # Speichern
    with open(ENV_PATH, "w") as f:
        f.write("# Gmail Helper Konfiguration\n")
        f.write("# Diese Datei wurde automatisch erstellt\n\n")
        f.write("# === Ollama ===\n")
        f.write(f"OLLAMA_BASE_URL={config['OLLAMA_BASE_URL']}\n")
        f.write(f"OLLAMA_MODEL={config['OLLAMA_MODEL']}\n\n")
        f.write("# === Gmail ===\n")
        f.write(f"GMAIL_Q={config['GMAIL_Q']}\n")
        f.write(f"MAX_RESULTS={config['MAX_RESULTS']}\n\n")
        f.write("# === Verhalten ===\n")
        f.write(f"DRY_RUN={config['DRY_RUN']}\n")
        f.write(f"SET_LABEL_COLORS={config['SET_LABEL_COLORS']}\n")
        f.write(f"LOG_LEVEL={config['LOG_LEVEL']}\n")
    
    print_success("Konfiguration gespeichert (.env)")
    return True


def run_test() -> bool:
    """Testlauf durchführen"""
    # Teste Ollama Verbindung
    print_info("Teste Ollama Verbindung...")
    returncode, stdout, _ = run_command(["curl", "-s", "http://localhost:11434/api/tags"])
    if returncode == 0:
        try:
            data = json.loads(stdout)
            models = [m.get("name", "") for m in data.get("models", [])]
            if models:
                print_success(f"Ollama läuft mit {len(models)} Modellen")
            else:
                print_warning("Ollama läuft, aber keine Modelle gefunden")
        except:
            print_success("Ollama erreichbar")
    else:
        print_error("Ollama nicht erreichbar")
        return False
    
    # Teste Gmail API
    print_info("Teste Gmail API (Dry-Run)...")
    python_exe = VENV_PATH / "bin" / "python"
    returncode, stdout, stderr = run_command(
        [str(python_exe), "-m", "app.main", "--dry-run", "--max-results", "1"],
        timeout=60
    )
    
    if returncode == 0:
        print_success("Gmail API funktioniert")
        # Extrahiere Info über gefundene E-Mails
        if "Gefundene Nachrichten" in stdout:
            for line in stdout.split("\n"):
                if "Gefundene Nachrichten" in line:
                    print_info(line.strip())
        return True
    else:
        print_error("Gmail API Test fehlgeschlagen")
        if stderr:
            print_info(f"Fehler: {stderr[:200]}")
        return False


def main() -> int:
    """Hauptfunktion"""
    parser = argparse.ArgumentParser(description="Gmail Helper Setup")
    parser.add_argument("--reset", action="store_true", 
                        help="Frage bei jedem Schritt ob neu konfiguriert werden soll (Token/Credentials bleiben erhalten)")
    args = parser.parse_args()
    
    skip_if_ok = not args.reset  # Bei --reset: immer fragen
    
    print(f"\n{BOLD}{CYAN}🚀 Gmail Helper Setup{NC}")
    print(f"{CYAN}{'═' * 55}{NC}\n")
    
    print("   Dieses Setup führt dich durch die Erstinstallation.")
    print("   Es werden folgende Komponenten eingerichtet:\n")
    print("   • Ollama (lokale KI)")
    print("   • Python Umgebung")
    print("   • KI-Modell (Download)")
    print("   • Gmail OAuth")
    print("   • Konfiguration\n")
    
    if args.reset:
        print(f"   {YELLOW}⚠️  Reset-Modus: Bestehende Werte werden angezeigt{NC}")
        print(f"   {YELLOW}    Du kannst pro Schritt wählen: behalten oder neu{NC}")
        print(f"   {YELLOW}    Token & Credentials bleiben erhalten!{NC}\n")
    
    if not ask_yes_no("Möchtest du das Setup starten?", default=True):
        print("   Abgebrochen.")
        return 0
    
    # Schritte durchführen
    steps = [
        ("System-Check", check_system),
        ("Ollama Setup", lambda: setup_ollama(skip_if_ok)),
        ("Python Environment", lambda: setup_python_env(skip_if_ok)),
        ("KI-Modell Download", lambda: download_model("qwen2.5:7b-instruct", skip_if_ok)),
        ("Gmail OAuth", lambda: setup_gmail_oauth(skip_if_ok)),
        ("Konfiguration", lambda: setup_config(skip_if_ok)),
        ("Testlauf", run_test),
    ]
    
    completed = 0
    for step_num, (name, func) in enumerate(steps, 1):
        print_step(step_num, len(steps), name)
        try:
            if not func():
                print()
                print_error(f"Setup bei '{name}' fehlgeschlagen")
                print()
                print(f"   {YELLOW}Du kannst das Setup jederzeit wiederholen:{NC}")
                if args.reset:
                    print(f"   gmailhelper setup")
                else:
                    print(f"   gmailhelper setup --reset  (um alle Einstellungen zu prüfen)")
                return 1
            completed += 1
        except KeyboardInterrupt:
            print()
            print_warning("Setup durch Benutzer unterbrochen")
            return 1
        except Exception as e:
            print()
            print_error(f"Fehler bei '{name}': {e}")
            return 1
    
    # Erfolgsmeldung
    print()
    print(f"{GREEN}{'═' * 55}{NC}")
    print(f"{GREEN}{BOLD}   ✨ Setup erfolgreich abgeschlossen!{NC}")
    print(f"{GREEN}{'═' * 55}{NC}")
    print()
    print("   Verfügbare Befehle:")
    print()
    print(f"   {CYAN}gmailhelper run --test{NC}")
    print("      Testlauf (zeigt an, setzt keine Labels)")
    print()
    print(f"   {CYAN}gmailhelper run --live{NC}")
    print("      Live-Betrieb (labels werden gesetzt)")
    print()
    print(f"   {CYAN}gmailhelper status{NC}")
    print("      Status anzeigen")
    print()
    print(f"   {CYAN}gmailhelper stop{NC}")
    print("      Dauerlauf stoppen")
    print()
    
    if not args.reset:
        print(f"   {DIM}Tipp: Mit 'gmailhelper setup --reset' kannst du{NC}")
        print(f"   {DIM}     später einzelne Einstellungen ändern.{NC}")
        print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
