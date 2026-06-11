# Veille Asso Jeunesse

Veille Asso Jeunesse est un outil gratuit de veille automatique pour les associations, ALSH, accueils enfance/jeunesse et structures d'éducation populaire.

Il lit des flux RSS/Atom, filtre les nouveautés avec des mots-clés, classe les résultats par catégorie, génère un mail HTML clair, puis l'envoie par SMTP. Il fonctionne sans IA par défaut. Une synthèse IA courte peut être ajoutée si une configuration IA est fournie.

## Démarrage Rapide Windows

1. Installez Python depuis [python.org/downloads/windows](https://www.python.org/downloads/windows/).
2. Pendant l'installation, cochez `Add python.exe to PATH`.
3. Ouvrez PowerShell dans le dossier du projet.
4. Lancez :

```powershell
.\scripts\install.ps1
.\scripts\launch_gui.ps1
```

L'interface graphique vous guide pour :

- tester les sources RSS ;
- configurer une adresse de test ;
- configurer le SMTP local dans `.env` ;
- tester le SMTP et envoyer un mail test ;
- générer `preview.html` ;
- préparer les secrets GitHub Actions.

Pour tester sans interface :

```powershell
.\scripts\test_local.ps1
```

## Déploiement GitHub Actions

1. Créez un dépôt à partir de ce projet ou utilisez-le comme template GitHub.
2. Modifiez les fichiers publics dans `config/`.
3. Dans GitHub, ouvrez `Settings` > `Secrets and variables` > `Actions`.
4. Ajoutez les secrets SMTP obligatoires :
   - `SMTP_HOST`
   - `SMTP_PORT`
   - `SMTP_USER`
   - `SMTP_PASSWORD`
   - `MAIL_FROM`
5. Ajoutez les secrets IA seulement si vous voulez activer les synthèses :
   - `AI_PROVIDER`
   - `AI_API_KEY`
   - `AI_MODEL`
   - `AI_BASE_URL`
6. Ouvrez l'onglet `Actions`, choisissez `Veille Asso Jeunesse`, puis cliquez sur `Run workflow`.

Le workflow vérifie la configuration avant d'envoyer un mail. Il refuse notamment les destinataires d'exemple du type `example.org`.

## Interface Graphique Locale

Lancement :

```powershell
.\scripts\launch_gui.ps1
```

L'interface permet de modifier :

- les sources RSS/Atom ;
- les destinataires ;
- les catégories et mots-clés ;
- les réglages du mail ;
- la configuration SMTP locale ;
- l'IA optionnelle.

Elle propose aussi :

- un assistant de première configuration ;
- un thème clair contrasté et un dark mode ;
- un test des sources ;
- un aperçu HTML du mail ;
- un dry-run sans modification de `data/seen_items.json`.

Les champs sensibles (`SMTP_PASSWORD`, `AI_API_KEY`) sont masqués par défaut et ne sont visibles qu'après clic sur le bouton d'affichage. Ils sont remasqués après enregistrement ou test.

## Fichiers De Configuration

Sources :

```yaml
sources:
  - name: "INJEP"
    url: "https://injep.fr/feed/"
    enabled: true
```

Catégories et mots-clés :

```yaml
categories:
  reglementation:
    label: "Réglementation et obligations"
    keywords:
      - "décret"
      - "arrêté"
      - "accueil collectif de mineurs"
```

Destinataires :

```yaml
recipients:
  - name: "Direction"
    email: "direction@example.org"
```

Remplacez toujours les adresses `example.org` avant un vrai envoi.

## Secrets Et Fichiers Locaux

Le fichier `.env` sert uniquement aux tests locaux. Il est ignoré par Git.

Variables SMTP :

```env
SMTP_HOST=smtp.example.org
SMTP_PORT=587
SMTP_USER=veille@example.org
SMTP_PASSWORD=mot-de-passe
MAIL_FROM=veille@example.org
```

Variables IA optionnelles :

```env
AI_PROVIDER=openrouter
AI_API_KEY=sk-...
AI_MODEL=openai/gpt-4o-mini
AI_BASE_URL=
```

Si `AI_PROVIDER` ou `AI_API_KEY` est vide, l'outil fonctionne sans IA.

## Commandes Utiles

Valider la configuration :

```powershell
python src/main.py --check-config
```

Tester sans envoyer de mail :

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

## Changer La Fréquence

La fréquence est dans `.github/workflows/veille.yml`.

Par défaut :

```yaml
schedule:
  - cron: "0 7 * * 1"
```

Les horaires GitHub Actions sont en UTC.

## IA Optionnelle

Fournisseurs compatibles OpenAI pris en charge :

| Fournisseur | `AI_PROVIDER` | `AI_BASE_URL` |
| --- | --- | --- |
| OpenAI | `openai` | Peut être laissé vide |
| OpenRouter | `openrouter` | Peut être laissé vide |
| Groq | `groq` | Peut être laissé vide |
| Mistral compatible | `mistral` | Peut être laissé vide |
| Custom compatible OpenAI | `custom` | Obligatoire |

En cas d'erreur IA, la veille continue sans synthèse pour l'élément concerné.

## Prudence Juridique

Cette veille est générée automatiquement. Elle aide au repérage d'informations réglementaires et pédagogiques. Elle ne remplace pas une analyse juridique, institutionnelle ou professionnelle. Les décisions doivent être prises à partir des sources officielles.

## Dépannage

### L'interface ne s'ouvre pas

- Vérifiez que Python vient de python.org.
- Lancez `python -c "import tkinter; print('OK')"` dans PowerShell.
- Relancez `.\scripts\install.ps1`.

### Le SMTP échoue

- Vérifiez le serveur, le port et le mot de passe.
- Utilisez un mot de passe d'application si votre messagerie l'exige.
- Testez depuis l'onglet `SMTP & expéditeur`.

### Le workflow GitHub échoue

- Vérifiez les secrets GitHub Actions.
- Remplacez les destinataires `example.org`.
- Lancez `python src/main.py --check-config` localement.

### Aucune nouveauté n'est trouvée

- Testez les sources dans l'interface.
- Activez temporairement `include_uncategorized` dans les réglages.
- Ajoutez des mots-clés dans `config/categories.yml`.
