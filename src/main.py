from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from ai_providers import enrich_items_with_ai_summaries
from classify_items import classify_items, load_categories
from fetch_sources import fetch_all_sources, load_sources
from generate_digest import render_digest, sort_items_by_date
from send_mail import get_smtp_config, load_recipients, send_email
from storage import filter_new_items, load_seen_items, mark_items_seen, save_seen_items
from validation import print_validation_result, validate_project


ROOT_DIR = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("veille-asso-jeunesse")


def main() -> int:
    args = _parse_args()
    load_dotenv(ROOT_DIR / ".env")
    settings = _load_yaml(ROOT_DIR / "config" / "settings.yml")
    _configure_logging(args.verbose)

    if args.check_config:
        result = validate_project(ROOT_DIR, require_smtp=not args.dry_run)
        print_validation_result(result)
        return 0 if result.ok else 1

    sources = load_sources(ROOT_DIR / "config" / "sources.yml")
    categories_config = load_categories(ROOT_DIR / "config" / "categories.yml")
    seen_path = ROOT_DIR / "data" / "seen_items.json"
    seen = load_seen_items(seen_path)

    LOGGER.info("%s source(s) active(s)", len(sources))
    fetched_items = fetch_all_sources(
        sources,
        timeout_seconds=int(settings.get("sources", {}).get("timeout_seconds", 20)),
        user_agent=str(settings.get("sources", {}).get("user_agent", "VeilleAssoJeunesse/1.0")),
    )
    new_items = filter_new_items(fetched_items, seen)
    LOGGER.info("%s element(s) nouveau(x) avant filtrage", len(new_items))

    processing_settings = settings.get("processing", {})
    include_uncategorized = bool(processing_settings.get("include_uncategorized", False))
    classified_items = classify_items(new_items, categories_config, include_uncategorized)
    classified_items = sort_items_by_date(classified_items)
    LOGGER.info("%s element(s) retenu(s) apres filtrage par mots-cles", len(classified_items))

    max_items = int(processing_settings.get("max_items_per_run", 60))
    items_to_send = classified_items[:max_items] if max_items > 0 else classified_items
    if len(classified_items) > len(items_to_send):
        LOGGER.info("%s element(s) garde(s) pour une prochaine execution", len(classified_items) - len(items_to_send))

    send_empty_digest = bool(settings.get("mail", {}).get("send_empty_digest", False))
    if items_to_send:
        items_to_send = enrich_items_with_ai_summaries(items_to_send, settings)

    should_render = bool(items_to_send or send_empty_digest or args.render_output)
    if should_render:
        subject, html_body = render_digest(
            items_to_send,
            settings,
            categories_config,
            ROOT_DIR / "templates" / "email.html",
        )
        recipients = load_recipients(ROOT_DIR / "config" / "recipients.yml")

        if args.render_output:
            render_path = Path(args.render_output)
            if not render_path.is_absolute():
                render_path = ROOT_DIR / render_path
            render_path.write_text(html_body, encoding="utf-8")
            LOGGER.info("Aperçu HTML généré: %s", render_path)

        if args.dry_run:
            send_email(subject, html_body, recipients, {}, dry_run=True)
        else:
            smtp_config = get_smtp_config(settings)
            send_email(subject, html_body, recipients, smtp_config)
            LOGGER.info("Mail envoye a %s destinataire(s)", len(recipients))
    else:
        LOGGER.info("Aucun element a envoyer.")

    if args.dry_run:
        LOGGER.info("Mode dry-run: data/seen_items.json n'est pas modifie.")
        return 0

    items_to_mark = _items_to_mark_as_seen(
        new_items=new_items,
        classified_items=classified_items,
        sent_items=items_to_send,
        mark_unmatched=bool(processing_settings.get("mark_unmatched_as_seen", True)),
    )
    if items_to_mark:
        mark_items_seen(seen, items_to_mark)
        save_seen_items(seen_path, seen)
        LOGGER.info("%s element(s) marque(s) comme vu(s)", len(items_to_mark))
    else:
        LOGGER.info("Aucun nouvel element a enregistrer comme vu.")

    return 0


def _items_to_mark_as_seen(
    new_items: list[dict[str, Any]],
    classified_items: list[dict[str, Any]],
    sent_items: list[dict[str, Any]],
    mark_unmatched: bool,
) -> list[dict[str, Any]]:
    sent_ids = {item.get("item_id") for item in sent_items}
    classified_ids = {item.get("item_id") for item in classified_items}

    items_to_mark = [item for item in sent_items if item.get("item_id")]

    if mark_unmatched:
        items_to_mark.extend(
            item
            for item in new_items
            if item.get("item_id") not in classified_ids and item.get("item_id") not in sent_ids
        )

    return items_to_mark


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Veille automatique pour associations et ALSH.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare la veille sans envoyer de mail ni modifier le suivi.")
    parser.add_argument("--verbose", action="store_true", help="Affiche plus de details dans les logs.")
    parser.add_argument("--check-config", action="store_true", help="Verifie la configuration sans lancer la veille.")
    parser.add_argument("--render-output", help="Genere un apercu HTML local du mail, par exemple preview.html.")
    return parser.parse_args()


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s - %(message)s",
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Execution interrompue: %s", exc)
        raise SystemExit(1) from exc
