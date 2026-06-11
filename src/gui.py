from __future__ import annotations

import json
import os
import smtplib
import ssl
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Any

import yaml

from ai_providers import OPENAI_COMPATIBLE_DEFAULT_BASE_URLS, get_ai_provider_from_env
from env_utils import build_secret_checklist, ensure_env_file, read_env_values, write_env_values
from fetch_sources import fetch_source
from send_mail import get_smtp_config, send_email


ROOT_DIR = Path(__file__).resolve().parents[1]
AI_PROVIDERS = {
    "Sans IA": "",
    "OpenAI": "openai",
    "OpenRouter": "openrouter",
    "Groq": "groq",
    "Mistral compatible": "mistral",
    "Custom compatible OpenAI": "custom",
}

THEMES = {
    "light": {
        "bg": "#f4f7fb",
        "panel": "#ffffff",
        "field": "#ffffff",
        "field_alt": "#f8fafc",
        "text": "#0f172a",
        "muted": "#475569",
        "border": "#94a3b8",
        "button": "#e2e8f0",
        "button_active": "#cbd5e1",
        "accent": "#1d4ed8",
        "accent_text": "#ffffff",
        "selection": "#bfdbfe",
        "ok": "#166534",
        "warning": "#b45309",
    },
    "dark": {
        "bg": "#0f172a",
        "panel": "#111827",
        "field": "#1f2937",
        "field_alt": "#172033",
        "text": "#f8fafc",
        "muted": "#cbd5e1",
        "border": "#475569",
        "button": "#334155",
        "button_active": "#475569",
        "accent": "#60a5fa",
        "accent_text": "#0f172a",
        "selection": "#1d4ed8",
        "ok": "#86efac",
        "warning": "#fbbf24",
    },
}


class VeilleGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Veille Asso Jeunesse - Configuration locale")
        self.geometry("1120x760")
        self.minsize(980, 640)

        self.sources_path = ROOT_DIR / "config" / "sources.yml"
        self.recipients_path = ROOT_DIR / "config" / "recipients.yml"
        self.categories_path = ROOT_DIR / "config" / "categories.yml"
        self.settings_path = ROOT_DIR / "config" / "settings.yml"
        self.env_path = ROOT_DIR / ".env"
        self.env_example_path = ROOT_DIR / ".env.example"
        self.gui_settings_path = ROOT_DIR / ".gui_settings.json"
        ensure_env_file(self.env_path, self.env_example_path)

        self.sources_data = self._load_yaml(self.sources_path)
        self.recipients_data = self._load_yaml(self.recipients_path)
        self.categories_data = self._load_yaml(self.categories_path)
        self.settings_data = self._load_yaml(self.settings_path)
        self.env_values = read_env_values(self.env_path)
        self.source_statuses: dict[int, str] = {}
        self.gui_settings = self.load_gui_settings()
        self.theme_name = self.gui_settings.get("theme", "light")
        if self.theme_name not in THEMES:
            self.theme_name = "light"
        self.colors = THEMES[self.theme_name]
        self.style = ttk.Style(self)
        self.text_widgets: list[tk.Text] = []
        self.list_widgets: list[tk.Listbox] = []
        self.tree_widgets: list[ttk.Treeview] = []
        self.help_labels: list[ttk.Label] = []
        self.smtp_secret_visible = False
        self.ai_secret_visible = False

        self._build_ui()
        self.apply_theme(self.theme_name)
        self.refresh_sources()
        self.refresh_recipients()
        self.refresh_categories()
        self.load_settings_form()
        self.load_env_form()
        self.refresh_setup_status()

    def _build_ui(self) -> None:
        self.top_bar = ttk.Frame(self, style="Top.TFrame", padding=(12, 10))
        self.top_bar.pack(fill="x")
        self.title_label = ttk.Label(self.top_bar, text="Veille Asso Jeunesse", style="Title.TLabel")
        self.title_label.pack(side="left")
        self.secret_notice_label = ttk.Label(
            self.top_bar,
            text="Secrets locaux dans .env - jamais envoyes sur GitHub",
            style="TopMuted.TLabel",
        )
        self.secret_notice_label.pack(side="left", padx=(18, 0))
        self.theme_button = ttk.Button(self.top_bar, command=self.toggle_theme)
        self.theme_button.pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.sources_tab = ttk.Frame(self.notebook, padding=12)
        self.recipients_tab = ttk.Frame(self.notebook, padding=12)
        self.categories_tab = ttk.Frame(self.notebook, padding=12)
        self.settings_tab = ttk.Frame(self.notebook, padding=12)
        self.smtp_tab = ttk.Frame(self.notebook, padding=12)
        self.ai_tab = ttk.Frame(self.notebook, padding=12)
        self.setup_tab = ttk.Frame(self.notebook, padding=12)
        self.assistant_tab = ttk.Frame(self.notebook, padding=12)
        self.test_tab = ttk.Frame(self.notebook, padding=12)

        self.notebook.add(self.sources_tab, text="Sources")
        self.notebook.add(self.recipients_tab, text="Destinataires")
        self.notebook.add(self.categories_tab, text="Categories")
        self.notebook.add(self.settings_tab, text="Reglages")
        self.notebook.add(self.smtp_tab, text="SMTP & expediteur")
        self.notebook.add(self.ai_tab, text="IA optionnelle")
        self.notebook.add(self.setup_tab, text="Mise en route")
        self.notebook.add(self.assistant_tab, text="Assistant")
        self.notebook.add(self.test_tab, text="Tester")

        self._build_sources_tab()
        self._build_recipients_tab()
        self._build_categories_tab()
        self._build_settings_tab()
        self._build_smtp_tab()
        self._build_ai_tab()
        self._build_setup_tab()
        self._build_assistant_tab()
        self._build_test_tab()

    def _build_sources_tab(self) -> None:
        columns = ("enabled", "status", "name", "url", "description")
        self.sources_tree = ttk.Treeview(self.sources_tab, columns=columns, show="headings", height=18)
        for column, label, width in (
            ("enabled", "Active", 70),
            ("status", "Dernier test", 150),
            ("name", "Nom", 170),
            ("url", "URL", 350),
            ("description", "Description", 300),
        ):
            self.sources_tree.heading(column, text=label)
            self.sources_tree.column(column, width=width, anchor="center" if column == "enabled" else "w")
        self.tree_widgets.append(self.sources_tree)
        self.sources_tree.pack(fill="both", expand=True)
        self.sources_tree.bind("<Double-1>", lambda _event: self.edit_source())

        buttons = ttk.Frame(self.sources_tab)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Ajouter", command=self.add_source).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Modifier", command=self.edit_source).pack(side="left", padx=6)
        ttk.Button(buttons, text="Activer / desactiver", command=self.toggle_source).pack(side="left", padx=6)
        ttk.Button(buttons, text="Tester les sources", command=self.test_sources).pack(side="left", padx=6)
        ttk.Button(buttons, text="Supprimer", command=self.delete_source).pack(side="left", padx=6)
        ttk.Button(buttons, text="Enregistrer", command=self.save_sources).pack(side="right")

    def _build_recipients_tab(self) -> None:
        self.recipients_tree = ttk.Treeview(self.recipients_tab, columns=("name", "email"), show="headings", height=18)
        self.recipients_tree.heading("name", text="Nom")
        self.recipients_tree.heading("email", text="Email")
        self.recipients_tree.column("name", width=320)
        self.recipients_tree.column("email", width=520)
        self.tree_widgets.append(self.recipients_tree)
        self.recipients_tree.pack(fill="both", expand=True)
        self.recipients_tree.bind("<Double-1>", lambda _event: self.edit_recipient())

        buttons = ttk.Frame(self.recipients_tab)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Ajouter", command=self.add_recipient).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Modifier", command=self.edit_recipient).pack(side="left", padx=6)
        ttk.Button(buttons, text="Supprimer", command=self.delete_recipient).pack(side="left", padx=6)
        ttk.Button(buttons, text="Enregistrer", command=self.save_recipients).pack(side="right")

    def _build_categories_tab(self) -> None:
        container = ttk.Frame(self.categories_tab)
        container.pack(fill="both", expand=True)

        left = ttk.Frame(container)
        left.pack(side="left", fill="y", padx=(0, 10))
        ttk.Label(left, text="Categories").pack(anchor="w")
        self.categories_list = tk.Listbox(left, width=34, height=22, exportselection=False)
        self.list_widgets.append(self.categories_list)
        self.categories_list.pack(fill="y", expand=True, pady=(6, 0))
        self.categories_list.bind("<<ListboxSelect>>", lambda _event: self.load_selected_category())

        right = ttk.Frame(container)
        right.pack(side="left", fill="both", expand=True)
        self.category_key_var = tk.StringVar()
        self.category_label_var = tk.StringVar()

        ttk.Label(right, text="Identifiant technique").pack(anchor="w")
        ttk.Entry(right, textvariable=self.category_key_var).pack(fill="x", pady=(2, 8))
        ttk.Label(right, text="Libelle affiche").pack(anchor="w")
        ttk.Entry(right, textvariable=self.category_label_var).pack(fill="x", pady=(2, 8))
        ttk.Label(right, text="Mots-cles, un par ligne").pack(anchor="w")
        self.category_keywords_text = tk.Text(right, height=16, wrap="word")
        self.text_widgets.append(self.category_keywords_text)
        self.category_keywords_text.pack(fill="both", expand=True, pady=(2, 0))

        buttons = ttk.Frame(self.categories_tab)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Nouvelle categorie", command=self.new_category).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Enregistrer la categorie", command=self.save_selected_category).pack(side="left", padx=6)
        ttk.Button(buttons, text="Supprimer", command=self.delete_category).pack(side="left", padx=6)
        ttk.Button(buttons, text="Enregistrer le fichier", command=self.save_categories).pack(side="right")

    def _build_settings_tab(self) -> None:
        self.subject_var = tk.StringVar()
        self.send_empty_var = tk.BooleanVar()
        self.include_uncategorized_var = tk.BooleanVar()
        self.mark_unmatched_var = tk.BooleanVar()
        self.max_items_var = tk.StringVar()
        self.ai_max_items_var = tk.StringVar()

        ttk.Label(self.settings_tab, text="Objet du mail").pack(anchor="w")
        ttk.Entry(self.settings_tab, textvariable=self.subject_var).pack(fill="x", pady=(2, 10))

        ttk.Label(self.settings_tab, text="Introduction").pack(anchor="w")
        self.intro_text = tk.Text(self.settings_tab, height=4, wrap="word")
        self.text_widgets.append(self.intro_text)
        self.intro_text.pack(fill="x", pady=(2, 10))

        ttk.Checkbutton(self.settings_tab, text="Envoyer un mail meme sans resultat", variable=self.send_empty_var).pack(anchor="w")
        ttk.Checkbutton(self.settings_tab, text="Inclure les elements sans categorie", variable=self.include_uncategorized_var).pack(anchor="w")
        ttk.Checkbutton(self.settings_tab, text="Marquer les elements non retenus comme deja vus", variable=self.mark_unmatched_var).pack(anchor="w", pady=(0, 10))

        row = ttk.Frame(self.settings_tab)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Maximum d'elements par envoi").pack(side="left")
        ttk.Entry(row, textvariable=self.max_items_var, width=8).pack(side="left", padx=(8, 24))
        ttk.Label(row, text="Maximum de syntheses IA").pack(side="left")
        ttk.Entry(row, textvariable=self.ai_max_items_var, width=8).pack(side="left", padx=(8, 0))

        ttk.Label(self.settings_tab, text="Mention de prudence juridique").pack(anchor="w")
        self.legal_notice_text = tk.Text(self.settings_tab, height=6, wrap="word")
        self.text_widgets.append(self.legal_notice_text)
        self.legal_notice_text.pack(fill="both", expand=True, pady=(2, 10))

        ttk.Button(self.settings_tab, text="Enregistrer", command=self.save_settings).pack(anchor="e")

    def _build_smtp_tab(self) -> None:
        self.smtp_host_var = tk.StringVar()
        self.smtp_port_var = tk.StringVar()
        self.smtp_user_var = tk.StringVar()
        self.smtp_password_var = tk.StringVar()
        self.mail_from_var = tk.StringVar()
        self.reply_to_var = tk.StringVar()
        self.smtp_tls_var = tk.BooleanVar()
        self.smtp_timeout_var = tk.StringVar()

        form = ttk.Frame(self.smtp_tab)
        form.pack(fill="x")
        self._entry_row(form, "Serveur SMTP", self.smtp_host_var, 0)
        self._entry_row(form, "Port", self.smtp_port_var, 1, width=12)
        self._entry_row(form, "Identifiant SMTP", self.smtp_user_var, 2)
        self.smtp_password_entry = self._entry_row(form, "Mot de passe SMTP", self.smtp_password_var, 3, show="*")
        self._entry_row(form, "Adresse expediteur", self.mail_from_var, 4)
        self._entry_row(form, "Reply-To optionnel", self.reply_to_var, 5)
        self._entry_row(form, "Timeout secondes", self.smtp_timeout_var, 6, width=12)

        ttk.Checkbutton(form, text="Utiliser TLS/STARTTLS", variable=self.smtp_tls_var).grid(row=7, column=1, sticky="w", pady=4)
        self.smtp_reveal_button = ttk.Button(
            form,
            text="Afficher le mot de passe",
            command=self.toggle_smtp_password_visibility,
        )
        self.smtp_reveal_button.grid(row=8, column=1, sticky="w", pady=4)

        buttons = ttk.Frame(self.smtp_tab)
        buttons.pack(fill="x", pady=(14, 0))
        ttk.Button(buttons, text="Enregistrer dans .env", command=self.save_env_form).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Tester SMTP", command=self.test_smtp).pack(side="left", padx=6)
        ttk.Button(buttons, text="Envoyer un mail test", command=self.send_test_email).pack(side="left", padx=6)

        self.smtp_help_label = ttk.Label(
            self.smtp_tab,
            text=".env reste local sur ce PC et ne doit pas etre envoye sur GitHub.",
            style="Muted.TLabel",
        )
        self.help_labels.append(self.smtp_help_label)
        self.smtp_help_label.pack(anchor="w", pady=(16, 0))

    def _build_ai_tab(self) -> None:
        self.ai_enabled_var = tk.BooleanVar()
        self.ai_provider_label_var = tk.StringVar(value="Sans IA")
        self.ai_api_key_var = tk.StringVar()
        self.ai_model_var = tk.StringVar()
        self.ai_base_url_var = tk.StringVar()

        form = ttk.Frame(self.ai_tab)
        form.pack(fill="x")
        ttk.Checkbutton(form, text="Activer une synthese IA optionnelle", variable=self.ai_enabled_var, command=self.on_ai_toggle).grid(row=0, column=1, sticky="w", pady=(0, 8))
        ttk.Label(form, text="Fournisseur").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        provider_combo = ttk.Combobox(form, textvariable=self.ai_provider_label_var, values=list(AI_PROVIDERS), state="readonly", width=28)
        provider_combo.grid(row=1, column=1, sticky="w", pady=4)
        provider_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_ai_provider_change())
        self.ai_key_entry = self._entry_row(form, "Cle API IA", self.ai_api_key_var, 2, show="*")
        self._entry_row(form, "Modele IA", self.ai_model_var, 3)
        self._entry_row(form, "AI_BASE_URL", self.ai_base_url_var, 4)

        self.ai_reveal_button = ttk.Button(
            form,
            text="Afficher la cle API",
            command=self.toggle_ai_key_visibility,
        )
        self.ai_reveal_button.grid(row=5, column=1, sticky="w", pady=4)

        self.ai_help_label = ttk.Label(self.ai_tab, text="", style="Muted.TLabel", wraplength=900)
        self.help_labels.append(self.ai_help_label)
        self.ai_help_label.pack(anchor="w", pady=(10, 0))

        buttons = ttk.Frame(self.ai_tab)
        buttons.pack(fill="x", pady=(14, 0))
        ttk.Button(buttons, text="Enregistrer dans .env", command=self.save_env_form).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Tester la configuration IA", command=self.test_ai).pack(side="left", padx=6)

    def _build_setup_tab(self) -> None:
        left = ttk.Frame(self.setup_tab)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right = ttk.Frame(self.setup_tab)
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Etat de configuration").pack(anchor="w")
        self.setup_status_text = tk.Text(left, height=22, wrap="word")
        self.text_widgets.append(self.setup_status_text)
        self.setup_status_text.pack(fill="both", expand=True, pady=(6, 10))
        ttk.Button(left, text="Rafraichir l'etat", command=self.refresh_setup_status).pack(anchor="w")

        ttk.Label(right, text="Secrets GitHub Actions a recopier").pack(anchor="w")
        self.github_secrets_text = tk.Text(right, height=22, wrap="word")
        self.text_widgets.append(self.github_secrets_text)
        self.github_secrets_text.pack(fill="both", expand=True, pady=(6, 10))
        buttons = ttk.Frame(right)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Copier la liste des secrets", command=self.copy_github_secrets).pack(side="left")

    def _build_assistant_tab(self) -> None:
        ttk.Label(
            self.assistant_tab,
            text="Parcours conseillé pour préparer une première mise en service.",
            style="Title.TLabel",
        ).pack(anchor="w", pady=(0, 10))
        self.assistant_text = tk.Text(self.assistant_tab, height=22, wrap="word")
        self.text_widgets.append(self.assistant_text)
        self.assistant_text.pack(fill="both", expand=True, pady=(0, 10))
        buttons = ttk.Frame(self.assistant_tab)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Rafraîchir l'assistant", command=self.refresh_assistant).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Tester les sources", command=self.test_sources).pack(side="left", padx=6)
        ttk.Button(buttons, text="Générer un aperçu du mail", command=self.generate_preview).pack(side="left", padx=6)
        ttk.Button(buttons, text="Copier les secrets GitHub", command=self.copy_github_secrets).pack(side="left", padx=6)

    def _build_test_tab(self) -> None:
        ttk.Label(self.test_tab, text="Tests sans modification de data/seen_items.json.").pack(anchor="w")
        buttons = ttk.Frame(self.test_tab)
        buttons.pack(fill="x", pady=10)
        ttk.Button(buttons, text="Dry-run sans IA", command=lambda: self.run_dry_run(use_ai=False)).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Dry-run avec IA si configuree", command=lambda: self.run_dry_run(use_ai=True)).pack(side="left", padx=6)
        ttk.Button(buttons, text="Générer preview.html", command=self.generate_preview).pack(side="left", padx=6)
        ttk.Button(buttons, text="Rafraichir les prerequis", command=self.refresh_test_prerequisites).pack(side="left", padx=6)
        self.test_prerequisites_label = ttk.Label(self.test_tab, text="", style="Muted.TLabel", wraplength=980)
        self.help_labels.append(self.test_prerequisites_label)
        self.test_prerequisites_label.pack(anchor="w", pady=(0, 8))
        self.test_output = tk.Text(self.test_tab, height=24, wrap="word")
        self.text_widgets.append(self.test_output)
        self.test_output.pack(fill="both", expand=True)

    def refresh_sources(self) -> None:
        self.sources_tree.delete(*self.sources_tree.get_children())
        for index, source in enumerate(self.sources_data.get("sources", [])):
            self.sources_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    "Oui" if source.get("enabled", True) else "Non",
                    self.source_statuses.get(index, "Non testé"),
                    source.get("name", ""),
                    source.get("url", ""),
                    source.get("description", ""),
                ),
            )
        self.refresh_setup_status()

    def test_sources(self) -> None:
        sources = self.sources_data.get("sources", [])
        for index, source in enumerate(sources):
            if not source.get("enabled", True):
                self.source_statuses[index] = "Désactivée"
                continue
            items = fetch_source(
                source,
                timeout_seconds=int(self.settings_data.get("sources", {}).get("timeout_seconds", 20)),
                user_agent=str(self.settings_data.get("sources", {}).get("user_agent", "VeilleAssoJeunesse/1.0")),
            )
            self.source_statuses[index] = "OK - " + str(len(items)) + " élément(s)" if items else "Aucun élément ou erreur"
        self.refresh_sources()
        messagebox.showinfo("Test terminé", "Le test des sources est terminé. Consultez la colonne 'Dernier test'.")

    def add_source(self) -> None:
        source = SourceDialog(self, "Ajouter une source").result
        if source:
            self.sources_data.setdefault("sources", []).append(source)
            self.refresh_sources()

    def edit_source(self) -> None:
        index = self._selected_index(self.sources_tree)
        if index is None:
            return
        sources = self.sources_data.setdefault("sources", [])
        result = SourceDialog(self, "Modifier une source", sources[index]).result
        if result:
            sources[index] = result
            self.refresh_sources()

    def toggle_source(self) -> None:
        index = self._selected_index(self.sources_tree)
        if index is None:
            return
        source = self.sources_data.setdefault("sources", [])[index]
        source["enabled"] = not bool(source.get("enabled", True))
        self.refresh_sources()

    def delete_source(self) -> None:
        index = self._selected_index(self.sources_tree)
        if index is not None and messagebox.askyesno("Supprimer", "Supprimer cette source ?"):
            del self.sources_data.setdefault("sources", [])[index]
            self.refresh_sources()

    def save_sources(self) -> None:
        self._save_yaml(self.sources_path, self.sources_data)
        self.refresh_setup_status()
        messagebox.showinfo("Enregistre", "Les sources ont ete enregistrees.")

    def refresh_recipients(self) -> None:
        self.recipients_tree.delete(*self.recipients_tree.get_children())
        for index, recipient in enumerate(self.recipients_data.get("recipients", [])):
            self.recipients_tree.insert("", "end", iid=str(index), values=(recipient.get("name", ""), recipient.get("email", "")))
        self.refresh_setup_status()

    def add_recipient(self) -> None:
        recipient = RecipientDialog(self, "Ajouter un destinataire").result
        if recipient:
            self.recipients_data.setdefault("recipients", []).append(recipient)
            self.refresh_recipients()

    def edit_recipient(self) -> None:
        index = self._selected_index(self.recipients_tree)
        if index is None:
            return
        recipients = self.recipients_data.setdefault("recipients", [])
        result = RecipientDialog(self, "Modifier un destinataire", recipients[index]).result
        if result:
            recipients[index] = result
            self.refresh_recipients()

    def delete_recipient(self) -> None:
        index = self._selected_index(self.recipients_tree)
        if index is not None and messagebox.askyesno("Supprimer", "Supprimer ce destinataire ?"):
            del self.recipients_data.setdefault("recipients", [])[index]
            self.refresh_recipients()

    def save_recipients(self) -> None:
        self._save_yaml(self.recipients_path, self.recipients_data)
        self.refresh_setup_status()
        messagebox.showinfo("Enregistre", "Les destinataires ont ete enregistres.")

    def refresh_categories(self) -> None:
        self.categories_list.delete(0, tk.END)
        for key, category in self.categories_data.get("categories", {}).items():
            self.categories_list.insert(tk.END, f"{key} - {category.get('label', key)}")
        if self.categories_list.size():
            self.categories_list.selection_set(0)
            self.load_selected_category()

    def load_selected_category(self) -> None:
        key = self._selected_category_key()
        if not key:
            return
        category = self.categories_data.get("categories", {}).get(key, {})
        self.category_key_var.set(key)
        self.category_label_var.set(category.get("label", key))
        self.category_keywords_text.delete("1.0", tk.END)
        self.category_keywords_text.insert("1.0", "\n".join(category.get("keywords", [])))

    def new_category(self) -> None:
        key = simpledialog.askstring("Nouvelle categorie", "Identifiant technique, sans espace :")
        if not key:
            return
        key = key.strip()
        categories = self.categories_data.setdefault("categories", {})
        if key in categories:
            messagebox.showerror("Erreur", "Cette categorie existe deja.")
            return
        categories[key] = {"label": key.replace("_", " ").title(), "keywords": []}
        self.refresh_categories()

    def save_selected_category(self) -> None:
        old_key = self._selected_category_key()
        new_key = self.category_key_var.get().strip()
        if not new_key:
            messagebox.showerror("Erreur", "L'identifiant technique est obligatoire.")
            return

        categories = self.categories_data.setdefault("categories", {})
        if old_key and old_key != new_key:
            if new_key in categories:
                messagebox.showerror("Erreur", "Une categorie avec cet identifiant existe deja.")
                return
            categories[new_key] = categories.pop(old_key)

        categories[new_key] = {
            "label": self.category_label_var.get().strip() or new_key,
            "keywords": [line.strip() for line in self.category_keywords_text.get("1.0", tk.END).splitlines() if line.strip()],
        }
        self.refresh_categories()

    def delete_category(self) -> None:
        key = self._selected_category_key()
        if key and messagebox.askyesno("Supprimer", "Supprimer cette categorie ?"):
            self.categories_data.setdefault("categories", {}).pop(key, None)
            self.refresh_categories()

    def save_categories(self) -> None:
        self.save_selected_category()
        self._save_yaml(self.categories_path, self.categories_data)
        messagebox.showinfo("Enregistre", "Les categories ont ete enregistrees.")

    def load_settings_form(self) -> None:
        mail = self.settings_data.get("mail", {})
        processing = self.settings_data.get("processing", {})
        ai = self.settings_data.get("ai", {})
        smtp = self.settings_data.get("smtp", {})
        self.subject_var.set(mail.get("subject", ""))
        self.intro_text.delete("1.0", tk.END)
        self.intro_text.insert("1.0", mail.get("intro", ""))
        self.send_empty_var.set(bool(mail.get("send_empty_digest", False)))
        self.include_uncategorized_var.set(bool(processing.get("include_uncategorized", False)))
        self.mark_unmatched_var.set(bool(processing.get("mark_unmatched_as_seen", True)))
        self.max_items_var.set(str(processing.get("max_items_per_run", 60)))
        self.ai_max_items_var.set(str(ai.get("max_items_per_run", 10)))
        self.smtp_tls_var.set(bool(smtp.get("use_tls", True)) if hasattr(self, "smtp_tls_var") else True)
        self.smtp_timeout_var.set(str(smtp.get("timeout_seconds", 30)) if hasattr(self, "smtp_timeout_var") else "30")
        self.reply_to_var.set(mail.get("reply_to", "") if hasattr(self, "reply_to_var") else "")
        self.legal_notice_text.delete("1.0", tk.END)
        self.legal_notice_text.insert("1.0", self.settings_data.get("legal_notice", ""))

    def save_settings(self, show_message: bool = True) -> bool:
        try:
            max_items = int(self.max_items_var.get().strip())
            ai_max_items = int(self.ai_max_items_var.get().strip())
            timeout = int(self.smtp_timeout_var.get().strip())
        except ValueError:
            messagebox.showerror("Erreur", "Les limites et le timeout doivent etre des nombres entiers.")
            return False

        mail = self.settings_data.setdefault("mail", {})
        processing = self.settings_data.setdefault("processing", {})
        ai = self.settings_data.setdefault("ai", {})
        smtp = self.settings_data.setdefault("smtp", {})
        mail["subject"] = self.subject_var.get().strip()
        mail["intro"] = self.intro_text.get("1.0", tk.END).strip()
        mail["send_empty_digest"] = self.send_empty_var.get()
        mail["reply_to"] = self.reply_to_var.get().strip()
        processing["include_uncategorized"] = self.include_uncategorized_var.get()
        processing["mark_unmatched_as_seen"] = self.mark_unmatched_var.get()
        processing["max_items_per_run"] = max_items
        ai["max_items_per_run"] = ai_max_items
        smtp["use_tls"] = self.smtp_tls_var.get()
        smtp["timeout_seconds"] = timeout
        self.settings_data["legal_notice"] = self.legal_notice_text.get("1.0", tk.END).strip()
        self._save_yaml(self.settings_path, self.settings_data)
        self.refresh_setup_status()
        if show_message:
            messagebox.showinfo("Enregistre", "Les reglages ont ete enregistres.")
        return True

    def load_env_form(self) -> None:
        self.env_values = read_env_values(self.env_path)
        self.smtp_host_var.set(self.env_values.get("SMTP_HOST", ""))
        self.smtp_port_var.set(self.env_values.get("SMTP_PORT", "587"))
        self.smtp_user_var.set(self.env_values.get("SMTP_USER", ""))
        self.smtp_password_var.set(self.env_values.get("SMTP_PASSWORD", ""))
        self.mail_from_var.set(self.env_values.get("MAIL_FROM", ""))

        provider = self.env_values.get("AI_PROVIDER", "")
        label = next((name for name, value in AI_PROVIDERS.items() if value == provider), "Custom compatible OpenAI" if provider else "Sans IA")
        self.ai_enabled_var.set(bool(provider and self.env_values.get("AI_API_KEY")))
        self.ai_provider_label_var.set(label)
        self.ai_api_key_var.set(self.env_values.get("AI_API_KEY", ""))
        self.ai_model_var.set(self.env_values.get("AI_MODEL", ""))
        self.ai_base_url_var.set(self.env_values.get("AI_BASE_URL", ""))
        self.on_ai_provider_change()
        self.hide_secrets()
        self.refresh_test_prerequisites()

    def save_env_form(self) -> bool:
        if not self._validate_env_form():
            return False

        provider = self._selected_ai_provider()
        if not self.ai_enabled_var.get():
            provider = ""

        updates = {
            "SMTP_HOST": self.smtp_host_var.get().strip(),
            "SMTP_PORT": self.smtp_port_var.get().strip(),
            "SMTP_USER": self.smtp_user_var.get().strip(),
            "SMTP_PASSWORD": self.smtp_password_var.get(),
            "MAIL_FROM": self.mail_from_var.get().strip(),
            "AI_PROVIDER": provider,
            "AI_API_KEY": self.ai_api_key_var.get().strip() if provider else "",
            "AI_MODEL": self.ai_model_var.get().strip() if provider else "",
            "AI_BASE_URL": self.ai_base_url_var.get().strip() if provider else "",
        }
        write_env_values(self.env_path, updates)
        self.env_values = read_env_values(self.env_path)
        if not self.save_settings(show_message=False):
            return False
        self._apply_env_to_process()
        self.hide_secrets()
        self.refresh_setup_status()
        messagebox.showinfo("Enregistre", ".env local enregistre. Il reste ignore par Git.")
        return True

    def test_smtp(self) -> None:
        if not self.save_env_form():
            return
        try:
            config = get_smtp_config(self.settings_data)
            self._open_smtp_session(config).quit()
        except Exception as exc:  # noqa: BLE001
            self.hide_secrets()
            messagebox.showerror("SMTP en erreur", f"Connexion SMTP impossible :\n{exc}")
            return
        self.hide_secrets()
        messagebox.showinfo("SMTP OK", "La connexion SMTP et l'authentification ont reussi.")

    def send_test_email(self) -> None:
        if not self.save_env_form():
            return
        recipient = simpledialog.askstring("Mail test", "Adresse de destination du mail test :")
        if not recipient:
            return
        if "@" not in recipient:
            messagebox.showerror("Erreur", "Indiquez une adresse email valide.")
            return
        try:
            config = get_smtp_config(self.settings_data)
            send_email(
                "Test Veille Asso Jeunesse",
                "<p>Ceci est un mail de test envoye depuis l'interface locale.</p>",
                [recipient.strip()],
                config,
            )
        except Exception as exc:  # noqa: BLE001
            self.hide_secrets()
            messagebox.showerror("Mail test en erreur", f"Le mail test n'a pas pu etre envoye :\n{exc}")
            return
        self.hide_secrets()
        messagebox.showinfo("Mail test envoye", f"Mail test envoye a {recipient}.")

    def test_ai(self) -> None:
        if not self.save_env_form():
            return
        if not self.ai_enabled_var.get():
            messagebox.showinfo("IA desactivee", "Activez l'IA et renseignez une cle API pour tester.")
            return
        try:
            provider = get_ai_provider_from_env(self.settings_data)
            if provider is None:
                raise RuntimeError("Configuration IA incomplete.")
            result = provider.summarize_item(
                {
                    "title": "Test de configuration IA",
                    "source": "Interface locale",
                    "published": "",
                    "summary": "Court test technique pour verifier la connexion au fournisseur IA.",
                    "link": "",
                    "keywords_detected": ["test"],
                }
            )
        except Exception as exc:  # noqa: BLE001
            self.hide_secrets()
            messagebox.showerror("IA en erreur", f"Le test IA a echoue :\n{exc}")
            return
        self.hide_secrets()
        messagebox.showinfo("IA OK", "La configuration IA a repondu.\n\nResume : " + result.get("resume", "OK"))

    def refresh_setup_status(self) -> None:
        if not hasattr(self, "setup_status_text"):
            return
        self.env_values = read_env_values(self.env_path)
        active_sources = [source for source in self.sources_data.get("sources", []) if source.get("enabled", True)]
        recipients = [recipient for recipient in self.recipients_data.get("recipients", []) if recipient.get("email")]
        smtp_ok = all(self.env_values.get(key) for key in ("SMTP_HOST", "SMTP_PORT", "MAIL_FROM"))
        ai_enabled = bool(self.env_values.get("AI_PROVIDER") and self.env_values.get("AI_API_KEY"))
        seen_exists = (ROOT_DIR / "data" / "seen_items.json").exists()

        lines = [
            self._status_line(bool(active_sources), f"{len(active_sources)} source(s) active(s)"),
            self._status_line(bool(recipients), f"{len(recipients)} destinataire(s) configure(s)"),
            self._status_line(smtp_ok, "SMTP local renseigne" if smtp_ok else "SMTP local incomplet"),
            self._status_line(bool(self.env_values.get("SMTP_PASSWORD")), "Mot de passe SMTP renseigne" if self.env_values.get("SMTP_PASSWORD") else "Mot de passe SMTP absent"),
            self._status_line(seen_exists, "Fichier data/seen_items.json present"),
            self._status_line(ai_enabled, "Cle IA renseignee et IA activee" if ai_enabled else "IA optionnelle desactivee ou cle absente"),
            "",
            "Rappel : les secrets du fichier .env sont uniquement locaux.",
            "Pour GitHub Actions, creez les secrets dans Settings > Secrets and variables > Actions.",
        ]
        self.setup_status_text.delete("1.0", tk.END)
        self.setup_status_text.insert("1.0", "\n".join(lines))
        self._color_status_lines(self.setup_status_text)

        self.github_secrets_text.delete("1.0", tk.END)
        self.github_secrets_text.insert("1.0", build_secret_checklist(self.env_values))
        self.refresh_test_prerequisites()
        self.refresh_assistant()

    def copy_github_secrets(self) -> None:
        text = self.github_secrets_text.get("1.0", tk.END).strip()
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copie", "La liste des secrets GitHub a ete copiee.")

    def refresh_test_prerequisites(self) -> None:
        if not hasattr(self, "test_prerequisites_label"):
            return
        active_sources = [source for source in self.sources_data.get("sources", []) if source.get("enabled", True)]
        recipients = [recipient for recipient in self.recipients_data.get("recipients", []) if recipient.get("email")]
        missing = []
        if not active_sources:
            missing.append("aucune source active")
        if not recipients:
            missing.append("aucun destinataire")
        text = "Prerequis OK pour un dry-run." if not missing else "A verifier avant test : " + ", ".join(missing)
        self.test_prerequisites_label.config(text=text)

    def refresh_assistant(self) -> None:
        if not hasattr(self, "assistant_text"):
            return
        self.env_values = read_env_values(self.env_path)
        active_sources = [source for source in self.sources_data.get("sources", []) if source.get("enabled", True)]
        recipients = [recipient for recipient in self.recipients_data.get("recipients", []) if recipient.get("email")]
        has_example_recipient = any("example." in str(recipient.get("email", "") if isinstance(recipient, dict) else recipient) for recipient in self.recipients_data.get("recipients", []))
        smtp_ready = all(self.env_values.get(key) for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"))
        ai_ready = bool(self.env_values.get("AI_PROVIDER") and self.env_values.get("AI_API_KEY"))
        lines = [
            self._status_line(True, "Étape 1 - Python et dépendances: utilisez scripts/install.ps1 pour préparer le poste."),
            self._status_line(bool(active_sources), f"Étape 2 - Sources: {len(active_sources)} source(s) active(s)."),
            self._status_line(bool(recipients) and not has_example_recipient, "Étape 3 - Destinataire test: remplacez les adresses example.org avant un vrai envoi."),
            self._status_line(smtp_ready, "Étape 4 - SMTP: renseignez et testez l'onglet SMTP & expéditeur."),
            self._status_line(True, "Étape 5 - IA: optionnelle, laissez désactivée pour un premier essai."),
            self._status_line(ai_ready, "Info IA: clé renseignée." if ai_ready else "Info IA: aucune clé IA renseignée, fonctionnement sans IA."),
            self._status_line(True, "Étape 6 - Test: générez preview.html, lancez un dry-run, puis envoyez un mail test."),
            "",
            "Déploiement GitHub: recopiez les secrets listés dans l'onglet Mise en route, puis lancez le workflow manuellement.",
        ]
        self.assistant_text.delete("1.0", tk.END)
        self.assistant_text.insert("1.0", "\n".join(lines))
        self._color_status_lines(self.assistant_text)

    def generate_preview(self) -> None:
        self.test_output.delete("1.0", tk.END)
        self.test_output.insert(tk.END, "Génération de preview.html...\n\n")
        self.update_idletasks()
        env = os.environ.copy()
        env.update(read_env_values(self.env_path))
        env["AI_PROVIDER"] = ""
        env["AI_API_KEY"] = ""
        command = [sys.executable, str(ROOT_DIR / "src" / "main.py"), "--dry-run", "--render-output", "preview.html"]
        result = subprocess.run(command, cwd=ROOT_DIR, env=env, capture_output=True, text=True, check=False)
        output = (result.stdout or "") + (result.stderr or "")
        if hasattr(self, "test_output"):
            self.test_output.delete("1.0", tk.END)
            self.test_output.insert(tk.END, output or "Aucune sortie affichée.")
        if result.returncode == 0:
            messagebox.showinfo("Aperçu généré", "preview.html a été généré à la racine du projet.")
        else:
            messagebox.showerror("Erreur", "L'aperçu n'a pas pu être généré. Consultez le journal.")

    def run_dry_run(self, use_ai: bool) -> None:
        self.refresh_test_prerequisites()
        self.test_output.delete("1.0", tk.END)
        self.test_output.insert(tk.END, "Test en cours...\n\n")
        self.update_idletasks()

        env = os.environ.copy()
        env.update(read_env_values(self.env_path))
        if not use_ai:
            env["AI_PROVIDER"] = ""
            env["AI_API_KEY"] = ""
        command = [sys.executable, str(ROOT_DIR / "src" / "main.py"), "--dry-run", "--verbose"]
        result = subprocess.run(command, cwd=ROOT_DIR, env=env, capture_output=True, text=True, check=False)
        self.test_output.delete("1.0", tk.END)
        self.test_output.insert(tk.END, (result.stdout or "") + (result.stderr or "") or "Aucune sortie affichee.")
        if result.returncode == 0:
            messagebox.showinfo("Test termine", "Le test dry-run est termine.")
        else:
            messagebox.showerror("Test en erreur", "Le test a rencontre une erreur. Consultez le journal affiche.")

    def on_ai_toggle(self) -> None:
        if self.ai_enabled_var.get() and self.ai_provider_label_var.get() == "Sans IA":
            self.ai_provider_label_var.set("OpenAI")
        if not self.ai_enabled_var.get():
            self.ai_provider_label_var.set("Sans IA")
        self.hide_secrets()
        self.on_ai_provider_change()

    def on_ai_provider_change(self) -> None:
        self.hide_secrets()
        provider = self._selected_ai_provider()
        if provider:
            self.ai_enabled_var.set(True)
        else:
            self.ai_enabled_var.set(False)

        default_base_url = OPENAI_COMPATIBLE_DEFAULT_BASE_URLS.get(provider, "")
        if provider and provider != "custom" and not self.ai_base_url_var.get().strip():
            self.ai_base_url_var.set(default_base_url)
        if provider == "custom":
            help_text = "Custom : renseignez obligatoirement AI_BASE_URL, par exemple https://mon-fournisseur.example/v1."
        elif provider:
            help_text = f"{self.ai_provider_label_var.get()} : URL compatible OpenAI recommandee : {default_base_url}"
        else:
            help_text = "Sans IA : la veille fonctionne normalement, sans synthese automatique."
        self.ai_help_label.config(text=help_text)

    def toggle_smtp_password_visibility(self) -> None:
        self.smtp_secret_visible = not self.smtp_secret_visible
        self.smtp_password_entry.config(show="" if self.smtp_secret_visible else "*")
        self.smtp_reveal_button.config(text="Masquer le mot de passe" if self.smtp_secret_visible else "Afficher le mot de passe")

    def toggle_ai_key_visibility(self) -> None:
        self.ai_secret_visible = not self.ai_secret_visible
        self.ai_key_entry.config(show="" if self.ai_secret_visible else "*")
        self.ai_reveal_button.config(text="Masquer la cle API" if self.ai_secret_visible else "Afficher la cle API")

    def hide_secrets(self) -> None:
        self.smtp_secret_visible = False
        self.ai_secret_visible = False
        if hasattr(self, "smtp_password_entry"):
            self.smtp_password_entry.config(show="*")
        if hasattr(self, "ai_key_entry"):
            self.ai_key_entry.config(show="*")
        if hasattr(self, "smtp_reveal_button"):
            self.smtp_reveal_button.config(text="Afficher le mot de passe")
        if hasattr(self, "ai_reveal_button"):
            self.ai_reveal_button.config(text="Afficher la cle API")

    def toggle_theme(self) -> None:
        self.apply_theme("dark" if self.theme_name == "light" else "light")

    def apply_theme(self, theme_name: str) -> None:
        self.theme_name = theme_name if theme_name in THEMES else "light"
        self.colors = THEMES[self.theme_name]
        self.configure(bg=self.colors["bg"])
        self.style.theme_use("clam")
        self._configure_ttk_styles()
        for widget in self.text_widgets:
            self.style_text_widget(widget)
        for widget in self.list_widgets:
            self.style_list_widget(widget)
        for tree in self.tree_widgets:
            tree.tag_configure("normal", background=self.colors["field"], foreground=self.colors["text"])
        if hasattr(self, "theme_button"):
            self.theme_button.config(text="Mode clair" if self.theme_name == "dark" else "Mode sombre")
        self.save_gui_settings()

    def _configure_ttk_styles(self) -> None:
        c = self.colors
        self.style.configure(".", background=c["bg"], foreground=c["text"], fieldbackground=c["field"])
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("Top.TFrame", background=c["panel"])
        self.style.configure("TLabel", background=c["bg"], foreground=c["text"])
        self.style.configure("Title.TLabel", background=c["panel"], foreground=c["text"], font=("Segoe UI", 14, "bold"))
        self.style.configure("Muted.TLabel", background=c["bg"], foreground=c["muted"])
        self.style.configure("TopMuted.TLabel", background=c["panel"], foreground=c["muted"])
        self.style.configure("TButton", background=c["button"], foreground=c["text"], bordercolor=c["border"], focusthickness=2, focuscolor=c["accent"])
        self.style.map("TButton", background=[("active", c["button_active"])], foreground=[("active", c["text"])])
        self.style.configure("TCheckbutton", background=c["bg"], foreground=c["text"])
        self.style.map("TCheckbutton", background=[("active", c["bg"])], foreground=[("active", c["text"])])
        self.style.configure("TEntry", fieldbackground=c["field"], foreground=c["text"], bordercolor=c["border"], insertcolor=c["text"])
        self.style.configure("TCombobox", fieldbackground=c["field"], foreground=c["text"], background=c["button"], arrowcolor=c["text"], bordercolor=c["border"])
        self.style.map("TCombobox", fieldbackground=[("readonly", c["field"])], foreground=[("readonly", c["text"])], selectbackground=[("readonly", c["selection"])])
        self.style.configure("TNotebook", background=c["bg"], bordercolor=c["border"])
        self.style.configure("TNotebook.Tab", background=c["button"], foreground=c["text"], padding=(12, 7))
        self.style.map("TNotebook.Tab", background=[("selected", c["panel"]), ("active", c["button_active"])], foreground=[("selected", c["text"]), ("active", c["text"])])
        self.style.configure("Treeview", background=c["field"], foreground=c["text"], fieldbackground=c["field"], bordercolor=c["border"], rowheight=26)
        self.style.configure("Treeview.Heading", background=c["button"], foreground=c["text"], bordercolor=c["border"])
        self.style.map("Treeview", background=[("selected", c["selection"])], foreground=[("selected", c["accent_text"] if self.theme_name == "dark" else c["text"])])

    def style_text_widget(self, widget: tk.Text) -> None:
        c = self.colors
        widget.configure(
            background=c["field"],
            foreground=c["text"],
            insertbackground=c["text"],
            selectbackground=c["selection"],
            selectforeground=c["accent_text"] if self.theme_name == "dark" else c["text"],
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=c["border"],
            highlightcolor=c["accent"],
        )
        self._color_status_lines(widget)

    def style_list_widget(self, widget: tk.Listbox) -> None:
        c = self.colors
        widget.configure(
            background=c["field"],
            foreground=c["text"],
            selectbackground=c["selection"],
            selectforeground=c["accent_text"] if self.theme_name == "dark" else c["text"],
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=c["border"],
            highlightcolor=c["accent"],
        )

    def load_gui_settings(self) -> dict[str, str]:
        if not self.gui_settings_path.exists():
            return {}
        try:
            data = json.loads(self.gui_settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def save_gui_settings(self) -> None:
        self.gui_settings_path.write_text(json.dumps({"theme": self.theme_name}, indent=2) + "\n", encoding="utf-8")

    def _color_status_lines(self, widget: tk.Text) -> None:
        c = self.colors
        widget.tag_configure("status_ok", foreground=c["ok"])
        widget.tag_configure("status_warning", foreground=c["warning"])
        line_count = int(widget.index("end-1c").split(".", 1)[0])
        for line_number in range(1, line_count + 1):
            line_start = f"{line_number}.0"
            line_end = f"{line_number}.end"
            text = widget.get(line_start, line_end)
            if text.startswith("[OK]"):
                widget.tag_add("status_ok", line_start, line_end)
            elif text.startswith("[A verifier]"):
                widget.tag_add("status_warning", line_start, line_end)

    def _validate_env_form(self) -> bool:
        if self.smtp_port_var.get().strip() and not self.smtp_port_var.get().strip().isdigit():
            messagebox.showerror("Erreur", "SMTP_PORT doit etre un nombre.")
            return False
        if self.mail_from_var.get().strip() and "@" not in self.mail_from_var.get().strip():
            messagebox.showerror("Erreur", "MAIL_FROM doit etre une adresse email.")
            return False
        if self.reply_to_var.get().strip() and "@" not in self.reply_to_var.get().strip():
            messagebox.showerror("Erreur", "Reply-To doit etre une adresse email.")
            return False
        if self.ai_enabled_var.get():
            provider = self._selected_ai_provider()
            if not provider:
                messagebox.showerror("Erreur", "Choisissez un fournisseur IA ou desactivez l'IA.")
                return False
            if provider == "custom" and not self.ai_base_url_var.get().strip():
                messagebox.showerror("Erreur", "AI_BASE_URL est obligatoire pour un fournisseur custom.")
                return False
            if not self.ai_api_key_var.get().strip():
                messagebox.showerror("Erreur", "La cle API IA est obligatoire si l'IA est activee.")
                return False
        return True

    def _apply_env_to_process(self) -> None:
        for key, value in read_env_values(self.env_path).items():
            os.environ[key] = value

    def _open_smtp_session(self, config: dict[str, Any]) -> smtplib.SMTP:
        host = config["host"]
        port = int(config["port"])
        timeout = int(config.get("timeout_seconds", 30))
        context = ssl.create_default_context()
        if port == 465:
            server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=timeout)
            if config.get("use_tls", True):
                server.starttls(context=context)
        if config.get("user") and config.get("password"):
            server.login(config["user"], config["password"])
        return server

    def _selected_ai_provider(self) -> str:
        return AI_PROVIDERS.get(self.ai_provider_label_var.get(), "")

    def _status_line(self, ok: bool, label: str) -> str:
        return ("[OK] " if ok else "[A verifier] ") + label

    def _entry_row(self, parent: ttk.Frame, label: str, variable: tk.StringVar, row: int, width: int = 52, show: str | None = None) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
        entry = ttk.Entry(parent, textvariable=variable, width=width, show=show or "")
        entry.grid(row=row, column=1, sticky="ew", pady=4)
        parent.columnconfigure(1, weight=1)
        return entry

    def _selected_index(self, tree: ttk.Treeview) -> int | None:
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("Selection", "Selectionnez d'abord une ligne.")
            return None
        return int(selection[0])

    def _selected_category_key(self) -> str | None:
        selection = self.categories_list.curselection()
        if not selection:
            return None
        return self.categories_list.get(selection[0]).split(" - ", 1)[0]

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def _save_yaml(self, path: Path, data: dict[str, Any]) -> None:
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, indent=2), encoding="utf-8")


class SourceDialog(simpledialog.Dialog):
    def __init__(self, parent: tk.Misc, title: str, source: dict[str, Any] | None = None) -> None:
        self.source = source or {"enabled": True, "name": "", "url": "", "description": ""}
        self.result: dict[str, Any] | None = None
        super().__init__(parent, title)

    def body(self, master: tk.Misc) -> tk.Widget:
        self.enabled_var = tk.BooleanVar(value=bool(self.source.get("enabled", True)))
        self.name_var = tk.StringVar(value=self.source.get("name", ""))
        self.url_var = tk.StringVar(value=self.source.get("url", ""))
        self.description_var = tk.StringVar(value=self.source.get("description", ""))
        ttk.Checkbutton(master, text="Source active", variable=self.enabled_var).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(master, text="Nom").grid(row=1, column=0, sticky="w")
        ttk.Entry(master, textvariable=self.name_var, width=64).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(master, text="URL RSS/Atom").grid(row=2, column=0, sticky="w")
        ttk.Entry(master, textvariable=self.url_var, width=64).grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(master, text="Description").grid(row=3, column=0, sticky="w")
        ttk.Entry(master, textvariable=self.description_var, width=64).grid(row=3, column=1, sticky="ew", pady=4)
        return master

    def validate(self) -> bool:
        if not self.name_var.get().strip() or not self.url_var.get().strip():
            messagebox.showerror("Erreur", "Le nom et l'URL sont obligatoires.")
            return False
        return True

    def apply(self) -> None:
        self.result = {
            "name": self.name_var.get().strip(),
            "url": self.url_var.get().strip(),
            "enabled": self.enabled_var.get(),
            "description": self.description_var.get().strip(),
        }


class RecipientDialog(simpledialog.Dialog):
    def __init__(self, parent: tk.Misc, title: str, recipient: dict[str, Any] | None = None) -> None:
        self.recipient = recipient or {"name": "", "email": ""}
        self.result: dict[str, str] | None = None
        super().__init__(parent, title)

    def body(self, master: tk.Misc) -> tk.Widget:
        self.name_var = tk.StringVar(value=self.recipient.get("name", ""))
        self.email_var = tk.StringVar(value=self.recipient.get("email", ""))
        ttk.Label(master, text="Nom").grid(row=0, column=0, sticky="w")
        ttk.Entry(master, textvariable=self.name_var, width=54).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(master, text="Email").grid(row=1, column=0, sticky="w")
        ttk.Entry(master, textvariable=self.email_var, width=54).grid(row=1, column=1, sticky="ew", pady=4)
        return master

    def validate(self) -> bool:
        if "@" not in self.email_var.get():
            messagebox.showerror("Erreur", "Indiquez une adresse email valide.")
            return False
        return True

    def apply(self) -> None:
        self.result = {"name": self.name_var.get().strip(), "email": self.email_var.get().strip()}


if __name__ == "__main__":
    VeilleGui().mainloop()
