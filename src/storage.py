from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SeenItems = dict[str, str]


def compute_item_id(item: dict) -> str:
    """Build a stable identifier for an item, even when a feed has no GUID."""
    candidates = [
        item.get("uid"),
        item.get("guid"),
        item.get("id"),
        item.get("link"),
    ]
    raw = next((str(value).strip() for value in candidates if str(value or "").strip()), "")

    if not raw:
        raw = " | ".join(
            str(value or "").strip()
            for value in (
                item.get("source"),
                item.get("title"),
                item.get("published"),
            )
        )

    normalized = raw.casefold().strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_seen_items(path: str | Path) -> SeenItems:
    seen_path = Path(path)
    if not seen_path.exists():
        return {}

    try:
        data = json.loads(seen_path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError:
        return {}

    if isinstance(data, list):
        return {str(item_id): "" for item_id in data}

    if isinstance(data, dict):
        items = data.get("items", data.get("seen", {}))
        if isinstance(items, list):
            return {str(item_id): "" for item_id in items}
        if isinstance(items, dict):
            return {str(item_id): str(seen_at or "") for item_id, seen_at in items.items()}

    return {}


def filter_new_items(items: Iterable[dict], seen: SeenItems | set[str]) -> list[dict]:
    seen_ids = set(seen.keys() if isinstance(seen, dict) else seen)
    new_items: list[dict] = []

    for item in items:
        item_id = item.get("item_id") or compute_item_id(item)
        item["item_id"] = item_id
        if item_id not in seen_ids:
            new_items.append(item)

    return new_items


def mark_items_seen(seen: SeenItems, items: Iterable[dict]) -> SeenItems:
    seen_at = datetime.now(timezone.utc).isoformat()
    for item in items:
        item_id = item.get("item_id") or compute_item_id(item)
        seen[str(item_id)] = seen_at
    return seen


def save_seen_items(path: str | Path, seen: SeenItems) -> None:
    seen_path = Path(path)
    seen_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": dict(sorted(seen.items())),
    }

    tmp_path = seen_path.with_suffix(seen_path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(seen_path)
