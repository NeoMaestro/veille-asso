from __future__ import annotations

import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import yaml


def load_recipients(path: str | Path) -> list[str]:
    recipient_path = Path(path)
    data = yaml.safe_load(recipient_path.read_text(encoding="utf-8")) or {}
    recipients = data.get("recipients", [])
    emails: list[str] = []

    for recipient in recipients:
        if isinstance(recipient, str):
            email = recipient.strip()
        else:
            email = str(recipient.get("email", "")).strip()

        if email:
            emails.append(email)

    return emails


def get_smtp_config(settings: dict[str, Any]) -> dict[str, Any]:
    smtp_settings = settings.get("smtp", {})
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587").strip() or "587")
    mail_from = os.getenv("MAIL_FROM", "").strip()

    if not host:
        raise RuntimeError("SMTP_HOST est obligatoire pour envoyer le mail.")
    if not mail_from:
        raise RuntimeError("MAIL_FROM est obligatoire pour envoyer le mail.")

    return {
        "host": host,
        "port": port,
        "user": os.getenv("SMTP_USER", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "mail_from": mail_from,
        "use_tls": bool(smtp_settings.get("use_tls", True)),
        "timeout_seconds": int(smtp_settings.get("timeout_seconds", 30)),
        "reply_to": str(settings.get("mail", {}).get("reply_to", "") or "").strip(),
    }


def send_email(
    subject: str,
    html_body: str,
    recipients: list[str],
    smtp_config: dict[str, Any],
    dry_run: bool = False,
) -> None:
    if not recipients:
        raise RuntimeError("Aucun destinataire configure dans config/recipients.yml.")

    if dry_run:
        print(f"[dry-run] Mail pret: {subject}")
        print(f"[dry-run] Destinataires: {', '.join(recipients)}")
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_config["mail_from"]
    message["To"] = ", ".join(recipients)
    if smtp_config.get("reply_to"):
        message["Reply-To"] = smtp_config["reply_to"]

    message.set_content(_html_to_text(html_body))
    message.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    host = smtp_config["host"]
    port = int(smtp_config["port"])
    timeout = int(smtp_config.get("timeout_seconds", 30))
    use_ssl = port == 465

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as server:
            _login_if_needed(server, smtp_config)
            server.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=timeout) as server:
        if smtp_config.get("use_tls", True):
            server.starttls(context=context)
        _login_if_needed(server, smtp_config)
        server.send_message(message)


def _login_if_needed(server: smtplib.SMTP, smtp_config: dict[str, Any]) -> None:
    user = smtp_config.get("user")
    password = smtp_config.get("password")
    if user and password:
        server.login(user, password)


def _html_to_text(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
