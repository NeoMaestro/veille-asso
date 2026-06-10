from __future__ import annotations

from pathlib import Path


DEFAULT_ENV_VALUES = {
    "SMTP_HOST": "smtp.example.org",
    "SMTP_PORT": "587",
    "SMTP_USER": "veille@example.org",
    "SMTP_PASSWORD": "change-me",
    "MAIL_FROM": "veille@example.org",
    "AI_PROVIDER": "",
    "AI_API_KEY": "",
    "AI_MODEL": "",
    "AI_BASE_URL": "",
}


def ensure_env_file(env_path: Path, example_path: Path | None = None) -> None:
    if env_path.exists():
        return

    if example_path and example_path.exists():
        env_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
        return

    lines = [f"{key}={value}" for key, value in DEFAULT_ENV_VALUES.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_env_values(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(line)
        if parsed:
            key, value = parsed
            values[key] = value
    return values


def write_env_values(env_path: Path, updates: dict[str, str]) -> None:
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    remaining_updates = dict(updates)
    new_lines: list[str] = []

    for line in existing_lines:
        parsed = _parse_env_line(line)
        if not parsed:
            new_lines.append(line)
            continue

        key, _value = parsed
        if key in remaining_updates:
            new_lines.append(f"{key}={_format_env_value(remaining_updates.pop(key, ''))}")
        else:
            new_lines.append(line)

    if remaining_updates and new_lines and new_lines[-1].strip():
        new_lines.append("")

    for key, value in remaining_updates.items():
        new_lines.append(f"{key}={_format_env_value(value)}")

    env_path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def build_secret_checklist(values: dict[str, str]) -> str:
    lines = [
        "Secrets GitHub Actions a creer dans le depot :",
        "",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "MAIL_FROM",
    ]

    if values.get("AI_PROVIDER") and values.get("AI_API_KEY"):
        lines.extend(
            [
                "",
                "Secrets IA optionnels :",
                "AI_PROVIDER",
                "AI_API_KEY",
                "AI_MODEL",
                "AI_BASE_URL",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "IA optionnelle non activee localement :",
                "ne creez les secrets AI_PROVIDER, AI_API_KEY, AI_MODEL et AI_BASE_URL que si vous souhaitez activer l'IA.",
            ]
        )

    return "\n".join(lines)


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in line:
        return None

    key, value = line.split("=", 1)
    key = key.strip()
    if not key:
        return None

    return key, _unquote_env_value(value.strip())


def _unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.replace(r"\"", '"').replace(r"\n", "\n")


def _format_env_value(value: str) -> str:
    value = str(value or "")
    if not value:
        return ""
    if any(char.isspace() for char in value) or "#" in value:
        return '"' + value.replace("\\", "\\\\").replace('"', r"\"") + '"'
    return value
