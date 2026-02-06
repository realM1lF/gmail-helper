from __future__ import annotations

import argparse
import logging
from typing import Dict, List, Set

from dotenv import load_dotenv
import time

from .config import load_config
from .gmail_client import GmailClient, ALLOWED_LABEL_COLORS
from .classifier import Classifier


logger = logging.getLogger(__name__)


ALL_LABELS = [
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

# Nur Gmail-erlaubte Farben (ALLOWED_LABEL_COLORS); Textfarbe #ffffff für dunklere Töne
_DARK_BG = frozenset({"#5484ed", "#46d6db", "#51b749", "#dc2127", "#4986e7", "#ac725e", "#cd74e6"})
LABEL_COLORS = {}
for i, name in enumerate(ALL_LABELS):
    bg = ALLOWED_LABEL_COLORS[i % len(ALLOWED_LABEL_COLORS)]
    txt = "#ffffff" if bg in _DARK_BG else "#000000"
    LABEL_COLORS[name] = {"backgroundColor": bg, "textColor": txt}


def run(dry_run_cli: bool | None = None, q_cli: str | None = None, max_results_cli: int | None = None) -> None:
    load_dotenv()
    cfg = load_config()

    # CLI-Flags überschreiben ENV/Defaults
    if dry_run_cli is not None:
        cfg.dry_run = dry_run_cli
    if q_cli:
        cfg.gmail_query = q_cli
    if max_results_cli is not None:
        cfg.max_results = max_results_cli

    logger.info("Starte Gmail-Klassifikation | dry_run=%s | q=%.80s | max=%d", cfg.dry_run, cfg.gmail_query, cfg.max_results)

    gmail = GmailClient()
    name_to_id = gmail.ensure_labels(ALL_LABELS, colors=None)
    logger.info("Vorhandene/angelegte Labels: %s", ", ".join(sorted(name_to_id.keys())))

    allowed = [l for l in ALL_LABELS if l != "Sonstiges"] + ["Sonstiges"]
    classifier = Classifier(
        labels_allowed=allowed,
        ollama_base_url=cfg.ollama_base_url,
        ollama_model=cfg.ollama_model,
    )

    effective_max = min(cfg.max_results, 20)
    # PASS 1: Unread der letzten 2 Tage
    message_ids = gmail.list_new_message_ids(cfg.gmail_query, effective_max)
    logger.info("Gefundene Nachrichten: %d (q=%.120s)", len(message_ids), cfg.gmail_query)
    # Preview der ersten Betreffzeilen zur schnellen Diagnose
    preview_max = min(5, len(message_ids))
    for i in range(preview_max):
        try:
            subj, sndr, _body, _lbls, its = gmail.fetch_message_core(message_ids[i])
            logger.debug("Preview[%d]: %s | %s", i, subj[:120], sndr)
        except Exception as e:
            logger.debug("Preview[%d] Fehler: %s", i, e)
    if not message_ids:
        logger.info("Keine neuen Nachrichten gefunden.")
        return

    plan: Dict[str, List[str]] = {}
    remove_sonstiges: List[str] = []
    # Hilfs-Mapping für Label-ID → -Name
    id_to_name = {v: k for k, v in name_to_id.items()}

    for mid in message_ids:
        try:
            subject, sender, body, label_ids, internal_ts = gmail.fetch_message_core(mid)
            # Skip nur wenn bereits ein spezifisches User-Label (≠ Sonstiges, ≠ ai/*) existiert
            existing_user_labels = [id_to_name.get(lid, "") for lid in label_ids]
            has_specific = any(
                (lbl in ALL_LABELS) and (lbl != "Sonstiges")
                for lbl in existing_user_labels
            )
            if has_specific:
                logger.info("Skip (bereits spezifisch gelabelt): %s | %s | vorhanden=%s", mid, subject[:80], ", ".join(existing_user_labels))
                continue
            # Payload begrenzen
            safe_body = body[:1000]
            labels: Set[str] = set(classifier.classify(sender, subject, safe_body))
            logger.info("Klassifiziert: %s | %s -> %s", mid, subject[:80], ", ".join(sorted(labels)))
            # Wenn wir spezifische Labels haben, und 'Sonstiges' dabei ist, entferne Sonstiges
            if len(labels) > 1 and "Sonstiges" in labels:
                labels.discard("Sonstiges")
                remove_sonstiges.append(mid)
        except Exception as exc:
            logger.exception("Fehler bei Klassifikation, markiere als Warnung: %s", exc)
            labels = {"Warnung"}

        for label_name in labels:
            plan.setdefault(label_name, []).append(mid)

    if cfg.dry_run:
        for name, mids in plan.items():
            logger.info("[DRY-RUN] Würde Label '%s' zu %d Nachrichten hinzufügen", name, len(mids))
    else:
        # Sicherstellen, dass alle im Plan vorkommenden Labels existieren
        needed = set(plan.keys()) - set(name_to_id.keys())
        if needed:
            logger.info("Fehlende Labels werden angelegt: %s", ", ".join(sorted(needed)))
            extra_map = gmail.ensure_labels(list(needed), colors=None)
            name_to_id.update(extra_map)
        for name, mids in plan.items():
            if name not in name_to_id:
                logger.warning("Überspringe unbekanntes Label '%s' (keine ID)", name)
                continue
            gmail.batch_add_labels(mids, [name_to_id[name]])
        if remove_sonstiges:
            gmail.batch_modify(remove_sonstiges, remove_label_ids=[name_to_id.get("Sonstiges", "")])
        logger.info("Batch-Labeling abgeschlossen.")

    # PASS 2: Re-Label für bestehende 'Sonstiges' innerhalb 7 Tage
    q_relabel = "in:inbox label:Sonstiges newer_than:7d"
    message_ids2 = gmail.list_new_message_ids(q_relabel, effective_max)
    logger.info("Gefundene 'Sonstiges' zur Neuprüfung: %d (q=%.120s)", len(message_ids2), q_relabel)

    plan2: Dict[str, List[str]] = {}
    remove_sonstiges2: List[str] = []
    for mid in message_ids2:
        try:
            subject, sender, body, label_ids, internal_ts = gmail.fetch_message_core(mid)
            safe_body = body[:1000]
            labels2: Set[str] = set(classifier.classify(sender, subject, safe_body))
            # Wenn spezifische Labels gefunden wurden, Sonstiges entfernen
            if any(l for l in labels2 if l != "Sonstiges"):
                remove_sonstiges2.append(mid)
            if "Sonstiges" in labels2 and len(labels2) > 1:
                labels2.discard("Sonstiges")
            for name in labels2:
                plan2.setdefault(name, []).append(mid)
            logger.info("Re-Label: %s | %s -> %s", mid, subject[:80], ", ".join(sorted(labels2)))
        except Exception as exc:
            logger.exception("Fehler bei Re-Labeling: %s", exc)
            plan2.setdefault("Warnung", []).append(mid)

    if cfg.dry_run:
        for name, mids in plan2.items():
            logger.info("[DRY-RUN] (Re-Label) Würde Label '%s' zu %d Nachrichten hinzufügen", name, len(mids))
    else:
        # Sicherstellen, dass auch hier alle Labels existieren
        needed2 = set(plan2.keys()) - set(name_to_id.keys()) - {"Sonstiges"}
        if needed2:
            logger.info("Fehlende Labels (Re-Label) werden angelegt: %s", ", ".join(sorted(needed2)))
            extra_map2 = gmail.ensure_labels(list(needed2), colors=None)
            name_to_id.update(extra_map2)
        for name, mids in plan2.items():
            if name == "Sonstiges":
                continue
            if name not in name_to_id:
                logger.warning("Überspringe unbekanntes Label '%s' (keine ID) im Re-Label", name)
                continue
            gmail.batch_add_labels(mids, [name_to_id[name]])
        if remove_sonstiges2:
            gmail.batch_modify(remove_sonstiges2, remove_label_ids=[name_to_id.get("Sonstiges", "")])
        logger.info("Re-Labeling abgeschlossen.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Nur geplante Aktionen ausgeben, nichts schreiben")
    ap.add_argument("--q", default=None, help="Optional Gmail-Query überschreiben")
    ap.add_argument("--max-results", type=int, default=None, help="Max Anzahl Nachrichten")
    ap.add_argument("--loop", action="store_true", help="Im Intervall wiederholt ausführen (alle 30s)")
    ap.add_argument("--interval", type=int, default=30, help="Intervall in Sekunden für Loop-Modus")
    args = ap.parse_args()

    if args.loop:
        while True:
            start_ts = time.time()
            try:
                run(dry_run_cli=args.dry_run, q_cli=args.q, max_results_cli=args.max_results)
            except Exception as exc:
                logger.exception("Unbehandelter Fehler in Loop-Iteration: %s", exc)
            duration = time.time() - start_ts
            logger.info("Iteration beendet (%.1fs). Warte %ds bis zum nächsten Lauf ...", duration, max(5, args.interval))
            time.sleep(max(5, args.interval))
    else:
        run(dry_run_cli=args.dry_run, q_cli=args.q, max_results_cli=args.max_results)


if __name__ == "__main__":
    main()


