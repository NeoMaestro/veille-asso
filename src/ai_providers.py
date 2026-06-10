from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import requests


LOGGER = logging.getLogger(__name__)

OPENAI_COMPATIBLE_DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "mistral": "https://api.mistral.ai/v1",
}


@dataclass
class AIConfig:
    provider: str
    api_key: str
    model: str
    base_url: str
    timeout_seconds: int = 30


class AIProvider(ABC):
    @abstractmethod
    def summarize_item(self, item: dict[str, Any]) -> dict[str, str]:
        raise NotImplementedError


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, config: AIConfig) -> None:
        self.config = config

    def summarize_item(self, item: dict[str, Any]) -> dict[str, str]:
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.config.model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Tu aides des associations, ALSH et structures d'education populaire "
                        "a comprendre rapidement une information de veille. Reponds en francais, "
                        "de facon concise, factuelle et prudente."
                    ),
                },
                {
                    "role": "user",
                    "content": _build_summary_prompt(item),
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.provider == "openrouter":
            headers["X-Title"] = "Veille Asso Jeunesse"

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return _parse_summary_response(content)


class AnthropicProvider(AIProvider):
    def __init__(self, config: AIConfig) -> None:
        self.config = config

    def summarize_item(self, item: dict[str, Any]) -> dict[str, str]:
        raise NotImplementedError("Le fournisseur Anthropic n'est pas encore implemente.")


class GeminiProvider(AIProvider):
    def __init__(self, config: AIConfig) -> None:
        self.config = config

    def summarize_item(self, item: dict[str, Any]) -> dict[str, str]:
        raise NotImplementedError("Le fournisseur Gemini n'est pas encore implemente.")


def get_ai_provider_from_env(settings: dict[str, Any]) -> AIProvider | None:
    provider_name = os.getenv("AI_PROVIDER", "").strip().casefold()
    api_key = os.getenv("AI_API_KEY", "").strip()

    if not provider_name or not api_key:
        LOGGER.info("IA non configuree: fonctionnement sans synthese IA.")
        return None

    model = os.getenv("AI_MODEL", "").strip()
    if not model:
        LOGGER.warning("AI_MODEL est absent: synthese IA desactivee.")
        return None

    configured_base_url = os.getenv("AI_BASE_URL", "").strip()
    base_url = configured_base_url or OPENAI_COMPATIBLE_DEFAULT_BASE_URLS.get(provider_name, "")
    timeout_seconds = int(settings.get("ai", {}).get("timeout_seconds", 30))

    config = AIConfig(
        provider=provider_name,
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )

    if provider_name in OPENAI_COMPATIBLE_DEFAULT_BASE_URLS or provider_name in {"custom", "openai-compatible"}:
        if not config.base_url:
            LOGGER.warning("AI_BASE_URL est obligatoire pour le fournisseur IA '%s'.", provider_name)
            return None
        return OpenAICompatibleProvider(config)

    if provider_name == "anthropic":
        LOGGER.warning("Architecture Anthropic prevue, mais fournisseur non implemente dans cette version.")
        return None

    if provider_name == "gemini":
        LOGGER.warning("Architecture Gemini prevue, mais fournisseur non implemente dans cette version.")
        return None

    if configured_base_url:
        LOGGER.warning(
            "Fournisseur IA '%s' non reference, tentative en mode compatible OpenAI via AI_BASE_URL.",
            provider_name,
        )
        return OpenAICompatibleProvider(config)

    LOGGER.warning("Fournisseur IA non supporte: %s. Synthese IA desactivee.", provider_name)
    return None


def enrich_items_with_ai_summaries(
    items: list[dict[str, Any]],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    provider = get_ai_provider_from_env(settings)
    if provider is None:
        return items

    max_items = int(settings.get("ai", {}).get("max_items_per_run", 10))
    if max_items <= 0:
        return items

    for index, item in enumerate(items):
        if index >= max_items:
            break
        try:
            item["ai_summary"] = provider.summarize_item(item)
        except Exception as exc:  # noqa: BLE001 - IA errors must not stop the watch.
            LOGGER.warning("Synthese IA impossible pour '%s': %s", item.get("title", "Sans titre"), exc)

    return items


def _build_summary_prompt(item: dict[str, Any]) -> str:
    return f"""
Analyse cet element de veille pour une association, un ALSH ou une structure jeunesse.

Titre: {item.get("title", "")}
Source: {item.get("source", "")}
Date: {item.get("published", "")}
Extrait: {item.get("summary", "")}
Lien: {item.get("link", "")}
Mots-cles detectes: {", ".join(item.get("keywords_detected", []))}

Retourne uniquement un objet JSON valide avec ces cles:
- resume
- interet_association_alsh
- public_concerne
- niveau_attention
- action_conseillee

Le niveau_attention doit etre exactement: faible, moyen ou fort.
""".strip()


def _parse_summary_response(content: str) -> dict[str, str]:
    text = str(content or "").strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    json_text = match.group(0) if match else text

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return {
            "resume": text,
            "interet_association_alsh": "",
            "public_concerne": "",
            "niveau_attention": "",
            "action_conseillee": "",
        }

    return {
        "resume": str(parsed.get("resume", "")).strip(),
        "interet_association_alsh": str(parsed.get("interet_association_alsh", "")).strip(),
        "public_concerne": str(parsed.get("public_concerne", "")).strip(),
        "niveau_attention": _normalize_attention_level(parsed.get("niveau_attention", "")),
        "action_conseillee": str(parsed.get("action_conseillee", "")).strip(),
    }


def _normalize_attention_level(value: Any) -> str:
    normalized = str(value or "").strip().casefold()
    if normalized in {"faible", "moyen", "fort"}:
        return normalized
    return str(value or "").strip()
