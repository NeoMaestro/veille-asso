# Veille Asso Jeunesse

Veille Asso Jeunesse est un outil gratuit de veille automatique pour les associations, ALSH, accueils enfance/jeunesse et structures d'éducation populaire.

Il sert à repérer plus facilement des informations réglementaires, institutionnelles et pédagogiques à partir de flux RSS/Atom. Il filtre les nouveautés avec des mots-clés, classe les résultats par catégorie, évite les doublons, génère un mail HTML clair et peut l'envoyer automatiquement.

Par défaut, l'outil fonctionne **sans IA**. Une synthèse IA courte peut être ajoutée seulement si vous configurez volontairement un fournisseur IA.

## Démarrage Windows En 5 Minutes

1. Installez Python depuis [python.org/downloads/windows](https://www.python.org/downloads/windows/).
2. Pendant l'installation, cochez `Add python.exe to PATH`.
3. Ouvrez PowerShell dans le dossier du projet.
4. Lancez l'installation :

```powershell
.\scripts\install.ps1
```

5. Ouvrez l'interface graphique :

```powershell
.\scripts\launch_gui.ps1
```

Dans l'interface, commencez par l'onglet **Assistant**. Il vous guide dans l'ordre conseillé : sources, destinataire de test, SMTP, IA optionnelle, aperçu HTML, dry-run et préparation GitHub.

## Premier Test Local

Avant un vrai envoi, faites un test local sécurisé.

1. Dans l'onglet **Destinataires**, remplacez les adresses `example.org` par une vraie adresse de test.
2. Dans l'onglet **SMTP & expéditeur**, renseignez le serveur SMTP, le port, l'identifiant, le mot de passe et l'adresse expéditeur.
3. Cliquez sur **Tester SMTP**.
4. Cliquez sur **Envoyer un mail test**.
5. Dans l'onglet **Sources**, cliquez sur **Tester les sources**.
6. Dans l'onglet **Tester**, cliquez sur **Générer preview.html**.
7. Lancez un **Dry-run sans IA**.

Le dry-run prépare la veille sans envoyer le digest et sans modifier `data/seen_items.json`.

Vous pouvez aussi lancer le test local en ligne de commande :

```powershell
.\scripts\test_local.ps1
```

Ce script peut échouer si les destinataires sont encore en `example.org`. C'est volontaire : l'outil bloque les envois réels vers des adresses d'exemple.

## Déploiement GitHub Actions

1. Poussez le projet sur GitHub.
2. Dans GitHub, ouvrez `Settings` > `Secrets and variables` > `Actions`.
3. Ajoutez les secrets SMTP obligatoires :
   - `SMTP_HOST`
   - `SMTP_PORT`
   - `SMTP_USER`
   - `SMTP_PASSWORD`
   - `MAIL_FROM`
4. Ajoutez les secrets IA seulement si vous voulez activer les synthèses IA :
   - `AI_PROVIDER`
   - `AI_API_KEY`
   - `AI_MODEL`
   - `AI_BASE_URL`
5. Ouvrez l'onglet `Actions`.
6. Choisissez le workflow **Veille Asso Jeunesse**.
7. Cliquez sur **Run workflow** pour lancer un test manuel.

Le workflow vérifie la configuration avant l'envoi. Il échoue proprement si un secret obligatoire manque ou si les destinataires contiennent encore `example.org`.

Le workflow se lance aussi automatiquement chaque semaine selon `.github/workflows/veille.yml`.

## Interface Graphique

Lancement :

```powershell
.\scripts\launch_gui.ps1
```

L'interface permet de gérer :

- les sources RSS/Atom ;
- les destinataires ;
- les catégories et mots-clés ;
- les réglages du mail ;
- la configuration SMTP locale ;
- l'IA optionnelle ;
- le test des sources ;
- l'aperçu HTML du mail ;
- les dry-runs ;
- la liste des secrets GitHub à recopier.

Elle contient aussi :

- un onglet **Assistant** pour la première configuration ;
- un thème clair contrasté ;
- un dark mode ;
- un masquage automatique des mots de passe et clés API.

Les champs `SMTP_PASSWORD` et `AI_API_KEY` sont masqués par défaut. Ils ne sont visibles qu'après clic sur le bouton d'affichage, puis sont remasqués après enregistrement, test SMTP, test IA ou changement de fournisseur IA.

## Fichiers Publics Et Secrets Locaux

Les fichiers publics du projet sont dans `config/` :

- `config/sources.yml` : sources RSS/Atom ;
- `config/categories.yml` : catégories et mots-clés ;
- `config/recipients.yml` : destinataires ;
- `config/settings.yml` : réglages du mail, du filtrage, du SMTP et de l'IA.

Les informations sensibles locales sont dans `.env`.

Le fichier `.env` est créé et modifié par l'interface. Il est ignoré par Git et ne doit jamais être envoyé sur GitHub.

Le fichier `.gui_settings.json` mémorise seulement le thème de l'interface. Il est local, non sensible, et ignoré par Git.

## Commandes Utiles

Installer le projet localement :

```powershell
.\scripts\install.ps1
```

Ouvrir l'interface :

```powershell
.\scripts\launch_gui.ps1
```

Tester localement sans vrai envoi :

```powershell
.\scripts\test_local.ps1
```

Valider la configuration :

```powershell
python src/main.py --check-config
```

Valider la configuration sans exiger le SMTP :

```powershell
python src/main.py --check-config --dry-run
```

Lancer un dry-run :

```powershell
python src/main.py --dry-run
```

Générer un aperçu HTML :

```powershell
python src/main.py --dry-run --render-output preview.html
```

Lancer un vrai envoi local :

```powershell
python src/main.py
```

## Configuration Avancée

### Sources

Les sources se modifient dans `config/sources.yml` ou depuis l'interface.

```yaml
sources:
  - name: "INJEP"
    url: "https://injep.fr/feed/"
    enabled: true
```

Certaines sources institutionnelles sont désactivées par défaut si elles sont instables, bloquées ou si elles ne retournent pas d'éléments de manière fiable. Vous pouvez les réactiver après les avoir testées.

### Catégories Et Mots-Clés

Les catégories se modifient dans `config/categories.yml` ou depuis l'interface.

```yaml
categories:
  reglementation:
    label: "Réglementation et obligations"
    keywords:
      - "décret"
      - "arrêté"
      - "accueil collectif de mineurs"
```

Un élément est classé dans la première catégorie dont un mot-clé est détecté. Les accents et la casse sont ignorés pour faciliter la détection.

### Fréquence GitHub Actions

La fréquence est définie dans `.github/workflows/veille.yml`.

Par défaut :

```yaml
schedule:
  - cron: "0 7 * * 1"
```

Les horaires GitHub Actions sont en UTC.

### IA Optionnelle

L'IA est désactivée par défaut.

Fournisseurs compatibles OpenAI pris en charge :

| Fournisseur | `AI_PROVIDER` | `AI_BASE_URL` |
| --- | --- | --- |
| OpenAI | `openai` | Peut être laissé vide |
| OpenRouter | `openrouter` | Peut être laissé vide |
| Groq | `groq` | Peut être laissé vide |
| Mistral compatible | `mistral` | Peut être laissé vide |
| Custom compatible OpenAI | `custom` | Obligatoire |

En cas d'erreur IA, la veille continue sans synthèse pour l'élément concerné.

### Suivi Des Doublons

Le fichier `data/seen_items.json` contient les éléments déjà vus.

Après chaque exécution GitHub Actions, le workflow commit ce fichier s'il a changé. Cela évite de renvoyer les mêmes informations à chaque veille.

## Prudence Juridique

Cette veille est générée automatiquement. Elle aide au repérage d'informations réglementaires et pédagogiques. Elle ne remplace pas une analyse juridique, institutionnelle ou professionnelle. Les décisions doivent être prises à partir des sources officielles.

## Dépannage

### L'interface Ne S'ouvre Pas

- Vérifiez que Python vient de python.org.
- Vérifiez Tkinter :

```powershell
python -c "import tkinter; print('OK')"
```

- Relancez :

```powershell
.\scripts\install.ps1
```

### PowerShell Bloque Les Scripts

Dans PowerShell, lancez :

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Puis relancez le script.

### Le SMTP Échoue

- Vérifiez le serveur SMTP, le port et l'identifiant.
- Utilisez un mot de passe d'application si votre messagerie l'exige.
- Testez depuis l'onglet **SMTP & expéditeur**.

### GitHub Actions Échoue

- Vérifiez les secrets GitHub Actions.
- Remplacez les destinataires `example.org`.
- Lancez localement :

```powershell
python src/main.py --check-config
```

### Aucune Nouveauté N'est Trouvée

- Testez les sources dans l'interface.
- Ajoutez des mots-clés dans `config/categories.yml`.
- Activez temporairement `include_uncategorized` dans les réglages.

### `--check-config` Bloque Sur `example.org`

C'est voulu. Avant un vrai envoi, remplacez les adresses d'exemple dans `config/recipients.yml` ou depuis l'onglet **Destinataires**.
