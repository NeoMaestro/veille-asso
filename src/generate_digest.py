from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


DEFAULT_LEGAL_NOTICE = (
    "Cette veille est générée automatiquement. Elle aide au repérage d’informations "
    "réglementaires et pédagogiques. Elle ne remplace pas une analyse juridique, "
    "institutionnelle ou professionnelle. Les décisions doivent être prises à partir "
    "des sources officielles."
)


def render_digest(
    items: list[dict[str, Any]],
    settings: dict[str, Any],
    categories_config: dict[str, Any],
    template_path: str | Path,
) -> tuple[str, str]:
    template_path = Path(template_path)
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["format_date"] = format_date
    env.filters["excerpt"] = excerpt

    mail_settings = settings.get("mail", {})
    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    today = datetime.now().strftime("%d/%m/%Y")
    grouped_items = group_items_by_category(items)

    subject_template = mail_settings.get(
        "subject",
        "Veille Asso Jeunesse - {date} - {count} nouveauté(s)",
    )
    subject = subject_template.format_map(
        _SafeFormatDict(
            {
                "date": today,
                "count": len(items),
            }
        )
    )

    template = env.get_template(template_path.name)
    html = template.render(
        title="Veille Asso Jeunesse",
        subject=subject,
        intro=mail_settings.get("intro", ""),
        generated_at=generated_at,
        total_items=len(items),
        grouped_items=grouped_items,
        categories_config=categories_config,
        legal_notice=settings.get("legal_notice", DEFAULT_LEGAL_NOTICE),
    )
    return subject, html


def group_items_by_category(items: list[dict[str, Any]]) -> OrderedDict[str, dict[str, Any]]:
    grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for item in sort_items_by_date(items):
        key = item.get("category_key", "autres")
        label = item.get("category_label", "Autres informations utiles")
        if key not in grouped:
            grouped[key] = {"label": label, "items": []}
        grouped[key]["items"].append(item)
    return grouped


def sort_items_by_date(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: _date_sort_key(item.get("published", "")), reverse=True)


def format_date(value: str) -> str:
    if not value:
        return "Date non indiquée"

    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)

    return dt.strftime("%d/%m/%Y")


def excerpt(value: str, max_length: int = 450) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def _date_sort_key(value: str) -> datetime:
    if not value:
        return datetime.min
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.min


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
