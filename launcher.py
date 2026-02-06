#!/usr/bin/env python3
"""
Gmail Helper Launcher – kleine UI für Ollama-Modell, .env und Start des Hauptprogramms.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

OLLAMA_MODELS = ["mistral:7b-instruct", "qwen2.5:7b-instruct", "llama3.1:8b", "qwen2.5:3b"]
OLLAMA_CHECK_URL = "http://localhost:11434"
OLLAMA_WAIT_SEC = 4


def load_env() -> dict[str, str]:
    """Liest .env in ein Dict (nur KEY=VALUE-Zeilen, keine Kommentare)."""
    out: dict[str, str] = {}
    if not ENV_PATH.exists():
        return out
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                out[key.strip()] = value.strip()
    return out


def save_env(env: dict[str, str]) -> None:
    """Schreibt .env aus dem Dict (erhält keine Kommentare)."""
    known_order = [
        "OLLAMA_BASE_URL", "OLLAMA_MODEL",
        "GMAIL_Q", "MAX_RESULTS", "DRY_RUN", "SET_LABEL_COLORS", "LOG_LEVEL",
    ]
    seen = set()
    lines: list[str] = []
    for key in known_order:
        if key in env:
            lines.append(f"{key}={env[key]}")
            seen.add(key)
    for key, value in sorted(env.items()):
        if key not in seen:
            lines.append(f"{key}={value}")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def is_ollama_reachable(base_url: str) -> bool:
    """Prüft, ob Ollama-API unter base_url erreichbar ist."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{base_url.rstrip('/')}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_ollama_serve() -> bool:
    """Startet 'ollama serve' im Hintergrund. Gibt True zurück wenn gestartet."""
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except FileNotFoundError:
        return False


def run_ui():
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox

    root = tk.Tk()
    root.title("Gmail Helper Launcher")
    root.minsize(400, 380)
    root.geometry("500x440")

    env = load_env()
    ollama_model_var = tk.StringVar(root, value=env.get("OLLAMA_MODEL", "qwen2.5:7b-instruct"))
    ollama_url_var = tk.StringVar(root, value=env.get("OLLAMA_BASE_URL", "http://localhost:11434"))
    dry_run_var = tk.BooleanVar(root, value=(env.get("DRY_RUN", "false").lower() in ("1", "true", "yes")))
    process_holder: list[subprocess.Popen | None] = [None]

    main = ttk.Frame(root, padding=12)
    main.pack(fill=tk.BOTH, expand=True)

    ttk.Label(main, text="Ollama Base-URL:").grid(row=0, column=0, sticky=tk.W, pady=(0, 4))
    ttk.Entry(main, textvariable=ollama_url_var, width=35).grid(row=1, column=0, sticky=tk.W, pady=(0, 4))
    ttk.Label(main, text="Ollama-Modell:").grid(row=2, column=0, sticky=tk.W, pady=(8, 4))
    ollama_combo = ttk.Combobox(main, textvariable=ollama_model_var, values=OLLAMA_MODELS, state="readonly", width=28)
    ollama_combo.grid(row=3, column=0, sticky=tk.W, pady=(0, 8))

    dry_frame = ttk.Frame(main)
    dry_frame.grid(row=4, column=0, sticky=tk.W, pady=(4, 12))
    ttk.Checkbutton(dry_frame, text="Dry-Run (nur anzeigen, keine Labels setzen)", variable=dry_run_var).pack(anchor=tk.W)

    def on_start():
        env = load_env()
        env["OLLAMA_MODEL"] = ollama_model_var.get()
        env["OLLAMA_BASE_URL"] = ollama_url_var.get().strip() or "http://localhost:11434"
        env["DRY_RUN"] = "true" if dry_run_var.get() else "false"
        save_env(env)

        base_url = env["OLLAMA_BASE_URL"]
        if not is_ollama_reachable(base_url):
            log_area.insert(tk.END, "Ollama nicht erreichbar – starte 'ollama serve' …\n")
            log_area.update()
            if not start_ollama_serve():
                messagebox.showerror("Ollama", "Konnte 'ollama serve' nicht starten (nicht im PATH?).")
                return
            for _ in range(OLLAMA_WAIT_SEC):
                time.sleep(1)
                if is_ollama_reachable(base_url):
                    log_area.insert(tk.END, "Ollama läuft.\n")
                    log_area.update()
                    break
            else:
                messagebox.showwarning("Ollama", "Ollama startet möglicherweise noch. Hauptprogramm wird trotzdem gestartet.")
        else:
            log_area.insert(tk.END, "Ollama bereits erreichbar.\n")
            log_area.update()

        log_area.insert(tk.END, "Starte Gmail Helper (alle 30s Prüfung) …\n")
        log_area.update()

        cmd = [sys.executable, "-m", "app.main", "--loop", "--interval", "30"]
        if dry_run_var.get():
            cmd.append("--dry-run")

        def run():
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env={**os.environ},
                )
                process_holder[0] = proc
                for line in proc.stdout:
                    log_area.insert(tk.END, line)
                    log_area.see(tk.END)
                    log_area.update_idletasks()
                proc.wait()
                if proc.returncode == 0:
                    log_area.insert(tk.END, "\n[Fertig.]\n")
                else:
                    log_area.insert(tk.END, f"\n[Beendet mit Code {proc.returncode}]\n")
            except Exception as e:
                log_area.insert(tk.END, f"\nFehler: {e}\n")
            finally:
                process_holder[0] = None

        threading.Thread(target=run, daemon=True).start()

    ttk.Button(main, text="START", command=on_start).grid(row=5, column=0, sticky=tk.W, pady=(0, 8))

    ttk.Label(main, text="Log:").grid(row=6, column=0, sticky=tk.W, pady=(8, 4))
    log_frame = ttk.Frame(main)
    log_frame.grid(row=7, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
    main.columnconfigure(0, weight=1)
    main.rowconfigure(7, weight=1)
    log_area = scrolledtext.ScrolledText(log_frame, height=12, width=60, wrap=tk.WORD, state=tk.NORMAL)
    log_area.pack(fill=tk.BOTH, expand=True)

    root.mainloop()


if __name__ == "__main__":
    run_ui()
