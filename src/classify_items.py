from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml


def load_categories(path: str | Path) -> dict[str, Any]:
    category_path = Path(path)
    data = yaml.safe_load(category_path.read_text(encoding="utf-8")) or {}
    if "categories" not in data:
        raise ValueError(f"Le fichier {category_path} doit contenir une cle 'categories'.")
    return data


def classify_items(
    items: list[dict[str, Any]],
    categories_config: dict[str, Any],
    include_uncategorized: bool = False,
) -> list[dict[str, Any]]:
    classified: list[dict[str, Any]] = []

    for item in items:
        classified_item = classify_item(item, categories_config, include_uncategorized)
        if classified_item:
            classified.append(classified_item)

    return classified


def classify_item(
    item: dict[str, Any],
    categories_config: dict[str, Any],
    include_uncategorized: bool = False,
) -> dict[str, Any] | None:
    text = _normalize_text(
        " ".join(
            [
                str(item.get("title", "")),
                str(item.get("summary", "")),
                str(item.get("source", "")),
            ]
        )
    )

    categories = categories_config.get("categories", {})
    for category_key, category in categories.items():
        keywords = category.get("keywords", [])
        detected = [keyword for keyword in keywords if _contains_keyword(text, str(keyword))]
        if detected:
            enriched = dict(item)
            enriched["category_key"] = category_key
            enriched["category_label"] = category.get("label", category_key)
            enriched["keywords_detected"] = _unique_preserve_order(detected)
            return enriched

    if not include_uncategorized:
        return None

    default_category = categories_config.get(
        "default_category",
        {"key": "autres", "label": "Autres informations utiles"},
    )
    enriched = dict(item)
    enriched["category_key"] = default_category.get("key", "autres")
    enriched["category_label"] = default_category.get("label", "Autres informations utiles")
    enriched["keywords_detected"] = []
    return enriched


def _contains_keyword(normalized_text: str, keyword: str) -> bool:
    normalized_keyword = _normalize_text(keyword)
    if not normalized_keyword:
        return False

    if normalized_keyword.isalnum() and len(normalized_keyword) <= 4:
        return re.search(rf"\b{re.escape(normalized_keyword)}\b", normalized_text) is not None

    return normalized_keyword in normalized_text


def _normalize_text(value: str) -> str:
    without_accents = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return without_accents.casefold()


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        marker = _normalize_text(value)
        if marker not in seen:
            seen.add(marker)
            unique.append(value)
    return unique
