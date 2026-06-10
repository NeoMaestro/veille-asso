from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]


class VeilleGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Veille Asso Jeunesse - Configuration locale")
        self.geometry("980x680")
        self.minsize(860, 560)

        self.sources_path = ROOT_DIR / "config" / "sources.yml"
        self.recipients_path = ROOT_DIR / "config" / "recipients.yml"
        self.categories_path = ROOT_DIR / "config" / "categories.yml"
        self.settings_path = ROOT_DIR / "config" / "settings.yml"

        self.sources_data = self._load_yaml(self.sources_path)
        self.recipients_data = self._load_yaml(self.recipients_path)
        self.categories_data = self._load_yaml(self.categories_path)
        self.settings_data = self._load_yaml(self.settings_path)

        self._build_ui()
        self.refresh_sources()
        self.refresh_recipients()
        self.refresh_categories()
        self.load_settings_form()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.sources_tab = ttk.Frame(notebook, padding=10)
        self.recipients_tab = ttk.Frame(notebook, padding=10)
        self.categories_tab = ttk.Frame(notebook, padding=10)
        self.settings_tab = ttk.Frame(notebook, padding=10)
        self.test_tab = ttk.Frame(notebook, padding=10)

        notebook.add(self.sources_tab, text="Sources")
        notebook.add(self.recipients_tab, text="Destinataires")
        notebook.add(self.categories_tab, text="Catégories")
        notebook.add(self.settings_tab, text="Réglages")
        notebook.add(self.test_tab, text="Tester")

        self._build_sources_tab()
        self._build_recipients_tab()
        self._build_categories_tab()
        self._build_settings_tab()
        self._build_test_tab()

    def _build_sources_tab(self) -> None:
        columns = ("enabled", "name", "url", "description")
        self.sources_tree = ttk.Treeview(self.sources_tab, columns=columns, show="headings", height=18)
        for column, label, width in (
            ("enabled", "Active", 70),
            ("name", "Nom", 180),
            ("url", "URL", 360),
            ("description", "Description", 260),
        ):
            self.sources_tree.heading(column, text=label)
            self.sources_tree.column(column, width=width, anchor="center" if column == "enabled" else "w")
        self.sources_tree.pack(fill="both", expand=True)
        self.sources_tree.bind("<Double-1>", lambda _event: self.edit_source())

        buttons = ttk.Frame(self.sources_tab)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Ajouter", command=self.add_source).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Modifier", command=self.edit_source).pack(side="left", padx=6)
        ttk.Button(buttons, text="Activer / désactiver", command=self.toggle_source).pack(side="left", padx=6)
        ttk.Button(buttons, text="Supprimer", command=self.delete_source).pack(side="left", padx=6)
        ttk.Button(buttons, text="Enregistrer", command=self.save_sources).pack(side="right")

    def _build_recipients_tab(self) -> None:
        self.recipients_tree = ttk.Treeview(self.recipients_tab, columns=("name", "email"), show="headings", height=18)
        self.recipients_tree.heading("name", text="Nom")
        self.recipients_tree.heading("email", text="Email")
        self.recipients_tree.column("name", width=280)
        self.recipients_tree.column("email", width=420)
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
        ttk.Label(left, text="Catégories").pack(anchor="w")
        self.categories_list = tk.Listbox(left, width=32, height=22, exportselection=False)
        self.categories_list.pack(fill="y", expand=True, pady=(6, 0))
        self.categories_list.bind("<<ListboxSelect>>", lambda _event: self.load_selected_category())

        right = ttk.Frame(container)
        right.pack(side="left", fill="both", expand=True)
        self.category_key_var = tk.StringVar()
        self.category_label_var = tk.StringVar()

        ttk.Label(right, text="Identifiant technique").pack(anchor="w")
        ttk.Entry(right, textvariable=self.category_key_var).pack(fill="x", pady=(2, 8))
        ttk.Label(right, text="Libellé affiché").pack(anchor="w")
        ttk.Entry(right, textvariable=self.category_label_var).pack(fill="x", pady=(2, 8))
        ttk.Label(right, text="Mots-clés, un par ligne").pack(anchor="w")
        self.category_keywords_text = tk.Text(right, height=16, wrap="word")
        self.category_keywords_text.pack(fill="both", expand=True, pady=(2, 0))

        buttons = ttk.Frame(self.categories_tab)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Nouvelle catégorie", command=self.new_category).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Enregistrer la catégorie", command=self.save_selected_category).pack(side="left", padx=6)
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
        self.intro_text.pack(fill="x", pady=(2, 10))

        ttk.Checkbutton(self.settings_tab, text="Envoyer un mail même sans résultat", variable=self.send_empty_var).pack(anchor="w")
        ttk.Checkbutton(self.settings_tab, text="Inclure les éléments sans catégorie", variable=self.include_uncategorized_var).pack(anchor="w")
        ttk.Checkbutton(self.settings_tab, text="Marquer les éléments non retenus comme déjà vus", variable=self.mark_unmatched_var).pack(anchor="w", pady=(0, 10))

        row = ttk.Frame(self.settings_tab)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Maximum d'éléments par envoi").pack(side="left")
        ttk.Entry(row, textvariable=self.max_items_var, width=8).pack(side="left", padx=(8, 24))
        ttk.Label(row, text="Maximum de synthèses IA").pack(side="left")
        ttk.Entry(row, textvariable=self.ai_max_items_var, width=8).pack(side="left", padx=(8, 0))

        ttk.Label(self.settings_tab, text="Mention de prudence juridique").pack(anchor="w")
        self.legal_notice_text = tk.Text(self.settings_tab, height=6, wrap="word")
        self.legal_notice_text.pack(fill="both", expand=True, pady=(2, 10))

        ttk.Button(self.settings_tab, text="Enregistrer", command=self.save_settings).pack(anchor="e")

    def _build_test_tab(self) -> None:
        ttk.Label(self.test_tab, text="Test sans envoi de mail et sans modification de data/seen_items.json.").pack(anchor="w")
        ttk.Button(self.test_tab, text="Lancer un test dry-run", command=self.run_dry_run).pack(anchor="w", pady=10)
        self.test_output = tk.Text(self.test_tab, height=24, wrap="word")
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
                    source.get("name", ""),
                    source.get("url", ""),
                    source.get("description", ""),
                ),
            )

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
        messagebox.showinfo("Enregistré", "Les sources ont été enregistrées.")

    def refresh_recipients(self) -> None:
        self.recipients_tree.delete(*self.recipients_tree.get_children())
        for index, recipient in enumerate(self.recipients_data.get("recipients", [])):
            self.recipients_tree.insert("", "end", iid=str(index), values=(recipient.get("name", ""), recipient.get("email", "")))

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
        messagebox.showinfo("Enregistré", "Les destinataires ont été enregistrés.")

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
        key = simpledialog.askstring("Nouvelle catégorie", "Identifiant technique, sans espace :")
        if not key:
            return
        key = key.strip()
        categories = self.categories_data.setdefault("categories", {})
        if key in categories:
            messagebox.showerror("Erreur", "Cette catégorie existe déjà.")
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
                messagebox.showerror("Erreur", "Une catégorie avec cet identifiant existe déjà.")
                return
            categories[new_key] = categories.pop(old_key)

        categories[new_key] = {
            "label": self.category_label_var.get().strip() or new_key,
            "keywords": [line.strip() for line in self.category_keywords_text.get("1.0", tk.END).splitlines() if line.strip()],
        }
        self.refresh_categories()

    def delete_category(self) -> None:
        key = self._selected_category_key()
        if key and messagebox.askyesno("Supprimer", "Supprimer cette catégorie ?"):
            self.categories_data.setdefault("categories", {}).pop(key, None)
            self.refresh_categories()

    def save_categories(self) -> None:
        self.save_selected_category()
        self._save_yaml(self.categories_path, self.categories_data)
        messagebox.showinfo("Enregistré", "Les catégories ont été enregistrées.")

    def load_settings_form(self) -> None:
        mail = self.settings_data.get("mail", {})
        processing = self.settings_data.get("processing", {})
        ai = self.settings_data.get("ai", {})
        self.subject_var.set(mail.get("subject", ""))
        self.intro_text.delete("1.0", tk.END)
        self.intro_text.insert("1.0", mail.get("intro", ""))
        self.send_empty_var.set(bool(mail.get("send_empty_digest", False)))
        self.include_uncategorized_var.set(bool(processing.get("include_uncategorized", False)))
        self.mark_unmatched_var.set(bool(processing.get("mark_unmatched_as_seen", True)))
        self.max_items_var.set(str(processing.get("max_items_per_run", 60)))
        self.ai_max_items_var.set(str(ai.get("max_items_per_run", 10)))
        self.legal_notice_text.delete("1.0", tk.END)
        self.legal_notice_text.insert("1.0", self.settings_data.get("legal_notice", ""))

    def save_settings(self) -> None:
        try:
            max_items = int(self.max_items_var.get().strip())
            ai_max_items = int(self.ai_max_items_var.get().strip())
        except ValueError:
            messagebox.showerror("Erreur", "Les limites doivent être des nombres entiers.")
            return

        mail = self.settings_data.setdefault("mail", {})
        processing = self.settings_data.setdefault("processing", {})
        ai = self.settings_data.setdefault("ai", {})
        mail["subject"] = self.subject_var.get().strip()
        mail["intro"] = self.intro_text.get("1.0", tk.END).strip()
        mail["send_empty_digest"] = self.send_empty_var.get()
        processing["include_uncategorized"] = self.include_uncategorized_var.get()
        processing["mark_unmatched_as_seen"] = self.mark_unmatched_var.get()
        processing["max_items_per_run"] = max_items
        ai["max_items_per_run"] = ai_max_items
        self.settings_data["legal_notice"] = self.legal_notice_text.get("1.0", tk.END).strip()
        self._save_yaml(self.settings_path, self.settings_data)
        messagebox.showinfo("Enregistré", "Les réglages ont été enregistrés.")

    def run_dry_run(self) -> None:
        self.test_output.delete("1.0", tk.END)
        self.test_output.insert(tk.END, "Test en cours...\n\n")
        self.update_idletasks()
        command = [sys.executable, str(ROOT_DIR / "src" / "main.py"), "--dry-run", "--verbose"]
        result = subprocess.run(command, cwd=ROOT_DIR, capture_output=True, text=True, check=False)
        self.test_output.delete("1.0", tk.END)
        self.test_output.insert(tk.END, (result.stdout or "") + (result.stderr or "") or "Aucune sortie affichée.")
        if result.returncode == 0:
            messagebox.showinfo("Test terminé", "Le test dry-run est terminé.")
        else:
            messagebox.showerror("Test en erreur", "Le test a rencontré une erreur. Consultez le journal affiché.")

    def _selected_index(self, tree: ttk.Treeview) -> int | None:
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("Sélection", "Sélectionnez d'abord une ligne.")
            return None
        return int(selection[0])

    def _selected_category_key(self) -> str | None:
        selection = self.categories_list.curselection()
        if not selection:
            return None
        return self.categories_list.get(selection[0]).split(" - ", 1)[0]

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {} if path.exists() else {}

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
