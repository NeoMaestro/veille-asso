from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def validate_project(root_dir: Path, require_smtp: bool = True) -> ValidationResult:
    result = ValidationResult()
    _validate_sources(root_dir / "config" / "sources.yml", result)
    _validate_categories(root_dir / "config" / "categories.yml", result)
    _validate_recipients(root_dir / "config" / "recipients.yml", result)
    _validate_seen_items(root_dir / "data" / "seen_items.json", result)
    _validate_gitignore(root_dir / ".gitignore", result)
    if require_smtp:
        _validate_smtp_env(result)
    return result


def print_validation_result(result: ValidationResult) -> None:
    if result.ok:
        print("[OK] Configuration valide.")
    else:
        print("[ERREUR] Configuration invalide.")

    for message in result.errors:
        print(f"- ERREUR: {message}")
    for message in result.warnings:
        print(f"- ATTENTION: {message}")


def _validate_sources(path: Path, result: ValidationResult) -> None:
    data = _load_yaml(path, result)
    sources = data.get("sources", []) if isinstance(data, dict) else []
    if not isinstance(sources, list):
        result.add_error("config/sources.yml doit contenir une liste 'sources'.")
        return
    active_sources = [source for source in sources if isinstance(source, dict) and source.get("enabled", True)]
    if not active_sources:
        result.add_error("Aucune source active dans config/sources.yml.")
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            result.add_error(f"Source #{index}: format invalide.")
            continue
        if source.get("enabled", True) and not source.get("url"):
            result.add_error(f"Source #{index}: URL manquante.")


def _validate_categories(path: Path, result: ValidationResult) -> None:
    data = _load_yaml(path, result)
    categories = data.get("categories", {}) if isinstance(data, dict) else {}
    if not isinstance(categories, dict) or not categories:
        result.add_error("Aucune catégorie définie dans config/categories.yml.")
        return
    for key, category in categories.items():
        keywords = category.get("keywords", []) if isinstance(category, dict) else []
        if not keywords:
            result.add_warning(f"Catégorie '{key}': aucun mot-clé défini.")


def _validate_recipients(path: Path, result: ValidationResult) -> None:
    data = _load_yaml(path, result)
    recipients = data.get("recipients", []) if isinstance(data, dict) else []
    if not isinstance(recipients, list) or not recipients:
        result.add_error("Aucun destinataire dans config/recipients.yml.")
        return
    valid_emails = []
    has_example_email = False
    for recipient in recipients:
        email = recipient if isinstance(recipient, str) else str(recipient.get("email", "") if isinstance(recipient, dict) else "")
        email = email.strip()
        if not email or "@" not in email:
            result.add_error("Un destinataire contient une adresse email invalide.")
            continue
        valid_emails.append(email)
        if email.endswith("@example.org") or "example." in email:
            has_example_email = True
    if not valid_emails:
        result.add_error("Aucune adresse destinataire valide.")
    if has_example_email:
        result.add_error("Remplacez les adresses d'exemple dans config/recipients.yml avant un vrai envoi.")


def _validate_seen_items(path: Path, result: ValidationResult) -> None:
    if not path.exists():
        result.add_error("data/seen_items.json est absent.")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        result.add_error("data/seen_items.json n'est pas un JSON valide.")
        return
    if not isinstance(data, dict):
        result.add_error("data/seen_items.json doit contenir un objet JSON.")


def _validate_gitignore(path: Path, result: ValidationResult) -> None:
    if not path.exists():
        result.add_warning(".gitignore absent: vérifiez que .env n'est jamais commité.")
        return
    ignored = path.read_text(encoding="utf-8")
    for pattern in (".env", ".gui_settings.json", ".venv/", "preview.html"):
        if pattern not in ignored:
            result.add_warning(f".gitignore ne contient pas '{pattern}'.")


def _validate_smtp_env(result: ValidationResult) -> None:
    for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"):
        if not os.getenv(key, "").strip():
            result.add_error(f"Secret ou variable d'environnement manquant: {key}.")
    port = os.getenv("SMTP_PORT", "").strip()
    if port and not port.isdigit():
        result.add_error("SMTP_PORT doit être un nombre.")


def _load_yaml(path: Path, result: ValidationResult) -> dict[str, Any]:
    if not path.exists():
        result.add_error(f"{path.relative_to(path.parents[1])} est absent.")
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        result.add_error(f"{path.name} n'est pas un YAML valide: {exc}")
        return {}
