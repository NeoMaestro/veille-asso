from __future__ import annotations

import calendar
import logging
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

import feedparser
import requests
import yaml


LOGGER = logging.getLogger(__name__)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def load_sources(path: str | Path) -> list[dict[str, Any]]:
    source_path = Path(path)
    data = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError(f"Le fichier {source_path} doit contenir une liste 'sources'.")
    return [source for source in sources if source.get("enabled", True)]


def fetch_all_sources(
    sources: list[dict[str, Any]],
    timeout_seconds: int = 20,
    user_agent: str = "VeilleAssoJeunesse/1.0",
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for source in sources:
        items.extend(fetch_source(source, timeout_seconds, user_agent))
    return items


def fetch_source(
    source: dict[str, Any],
    timeout_seconds: int = 20,
    user_agent: str = "VeilleAssoJeunesse/1.0",
) -> list[dict[str, Any]]:
    url = str(source.get("url", "")).strip()
    name = str(source.get("name", url)).strip() or url

    if not url:
        LOGGER.warning("Source ignoree car l'URL est vide: %s", name)
        return []

    try:
        response = requests.get(
            url,
            timeout=timeout_seconds,
            headers={"User-Agent": user_agent},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.warning("Impossible de lire la source %s (%s): %s", name, url, exc)
        return []

    feed = feedparser.parse(response.content)
    if getattr(feed, "bozo", False):
        LOGGER.warning("Flux potentiellement invalide pour %s: %s", name, feed.get("bozo_exception"))

    feed_title = _clean_text(feed.feed.get("title", "")) if getattr(feed, "feed", None) else ""
    source_name = name or feed_title or url
    source_home = feed.feed.get("link", "") if getattr(feed, "feed", None) else ""

    normalized_items: list[dict[str, Any]] = []
    for entry in feed.entries:
        title = _clean_text(entry.get("title", "Sans titre"))
        link = str(entry.get("link", "")).strip()
        summary = _extract_summary(entry)

        if not title and not link:
            continue

        normalized_items.append(
            {
                "uid": str(entry.get("id") or entry.get("guid") or link or title),
                "title": title or "Sans titre",
                "link": link,
                "summary": summary,
                "source": source_name,
                "source_url": source_home,
                "feed_url": url,
                "published": _extract_date(entry),
            }
        )

    LOGGER.info("%s: %s element(s) lu(s)", source_name, len(normalized_items))
    return normalized_items


def _extract_summary(entry: Any) -> str:
    if entry.get("summary"):
        return _clean_text(entry.get("summary"))
    if entry.get("description"):
        return _clean_text(entry.get("description"))

    content = entry.get("content")
    if isinstance(content, list) and content:
        first_content = content[0]
        if isinstance(first_content, dict):
            return _clean_text(first_content.get("value", ""))

    return ""


def _extract_date(entry: Any) -> str:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if parsed:
            timestamp = calendar.timegm(parsed)
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    return ""


def _clean_text(value: Any) -> str:
    text = str(value or "")
    text = TAG_RE.sub(" ", text)
    text = unescape(text)
    return WHITESPACE_RE.sub(" ", text).strip()
