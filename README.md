# Veille Asso Jeunesse

Veille Asso Jeunesse est un outil gratuit de veille automatique pour les associations, ALSH, accueils enfance/jeunesse et structures d'education populaire.

Il lit des flux RSS ou Atom, repere les nouveautes utiles avec des mots-cles, les classe par categorie, genere un mail HTML clair, puis l'envoie automatiquement par SMTP. Il fonctionne sans IA par defaut. Une synthese IA courte peut etre ajoutee uniquement si vous fournissez une configuration IA.

## A quoi sert l'outil

L'outil aide a reperer plus facilement :

- les textes reglementaires ou institutionnels ;
- les informations concernant les accueils collectifs de mineurs, ALSH, periscolaire et extrascolaire ;
- les ressources pedagogiques utiles ;
- les appels a projets, subventions et informations associatives ;
- les sujets de prevention, inclusion, laicite, handicap, securite ou protection de l'enfance.

Le mail envoye contient les resultats regroupes par categories avec, pour chaque element, le titre, la source, la date, un extrait, les mots-cles detectes et le lien vers la source.

## Utilisation comme template GitHub

1. Publiez ce dossier dans un depot GitHub.
2. Dans GitHub, ouvrez `Settings` puis activez l'option `Template repository` si vous voulez le proposer comme modele.
3. Les personnes qui utiliseront le template pourront cliquer sur `Use this template`.
4. Elles modifieront ensuite les fichiers dans `config/` et ajouteront leurs secrets GitHub.
5. Le workflow GitHub Actions executera la veille chaque semaine.

## Configuration des sources

Les sources se modifient dans `config/sources.yml`.

Exemple :

```yaml
sources:
  - name: "INJEP"
    url: "https://injep.fr/feed/"
    enabled: true
```

Vous pouvez ajouter, supprimer ou desactiver une source avec `enabled: false`.

L'outil accepte les flux RSS et Atom. Si une source ne repond pas, elle est ignoree et les autres sources continuent d'etre traitees.

## Configuration des mots-cles

Les categories et mots-cles se modifient dans `config/categories.yml`.

Exemple :

```yaml
categories:
  reglementation:
    label: "Reglementation et obligations"
    keywords:
      - "decret"
      - "arrete"
      - "accueil collectif de mineurs"
```

Un element est classe dans la premiere categorie dont un mot-cle est detecte. Les accents et la casse sont ignores pour faciliter la detection.

## Configuration des destinataires

Les destinataires se modifient dans `config/recipients.yml`.

```yaml
recipients:
  - name: "Direction"
    email: "direction@example.org"
```

Vous pouvez ajouter plusieurs destinataires.

## Configuration SMTP

L'envoi du mail utilise des secrets GitHub ou un fichier `.env` en local.

Variables obligatoires :

| Variable | Role |
| --- | --- |
| `SMTP_HOST` | Serveur SMTP |
| `SMTP_PORT` | Port SMTP, souvent `587` |
| `SMTP_USER` | Identifiant SMTP |
| `SMTP_PASSWORD` | Mot de passe ou mot de passe d'application |
| `MAIL_FROM` | Adresse expediteur, par exemple `veille@example.org` |

Copiez `.env.example` en `.env` pour tester en local.

## Secrets GitHub

Dans votre depot GitHub :

1. Ouvrez `Settings`.
2. Allez dans `Secrets and variables`, puis `Actions`.
3. Ajoutez les secrets SMTP :
   - `SMTP_HOST`
   - `SMTP_PORT`
   - `SMTP_USER`
   - `SMTP_PASSWORD`
   - `MAIL_FROM`
4. Ajoutez les secrets IA seulement si vous voulez activer une synthese IA :
   - `AI_PROVIDER`
   - `AI_API_KEY`
   - `AI_MODEL`
   - `AI_BASE_URL`

Si `AI_PROVIDER` ou `AI_API_KEY` est absent, l'outil fonctionne sans IA.

## Lancement manuel

Dans GitHub :

1. Ouvrez l'onglet `Actions`.
2. Choisissez le workflow `Veille Asso Jeunesse`.
3. Cliquez sur `Run workflow`.

En local :

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python src/main.py --dry-run
python src/main.py
```

Sous Windows PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python src/main.py --dry-run
python src/main.py
```

Le mode `--dry-run` prepare la veille et affiche un resume sans envoyer de mail ni modifier `data/seen_items.json`.

## Interface graphique locale

Une interface graphique locale permet de modifier la configuration sans ouvrir les fichiers YAML a la main.

Elle permet de :

- ajouter, modifier, supprimer, activer ou desactiver les sources RSS/Atom ;
- modifier les destinataires ;
- modifier les categories et mots-cles ;
- ajuster quelques reglages du mail et du filtrage ;
- configurer le SMTP local dans `.env` ;
- configurer une cle IA optionnelle dans `.env` ;
- tester la connexion SMTP ;
- envoyer un mail test ;
- tester la configuration IA ;
- afficher la liste des secrets GitHub Actions a creer ;
- lancer un test `dry-run` avec ou sans IA, sans envoyer de mail.

Lancement :

```bash
python src/gui.py
```

Sous Windows PowerShell :

```powershell
python src/gui.py
```

L'interface modifie deux types de fichiers :

- `config/*.yml` pour les informations publiques du projet : sources, destinataires, categories et reglages ;
- `.env` pour les informations sensibles locales : SMTP, mot de passe SMTP et cle API IA.

Le fichier `.env` est ignore par Git et ne doit jamais etre envoye sur GitHub.

Apres modification des fichiers `config/*.yml`, il faut commit et push les changements pour les publier sur GitHub. Les valeurs de `.env`, elles, servent seulement aux tests locaux.

### Tester SMTP / Tester IA

Dans l'interface :

1. Ouvrez l'onglet `SMTP & expediteur`.
2. Renseignez le serveur SMTP, le port, l'identifiant, le mot de passe et l'adresse expediteur.
3. Cliquez sur `Tester SMTP` pour verifier la connexion.
4. Cliquez sur `Envoyer un mail test` pour verifier l'envoi reel.

Pour l'IA :

1. Ouvrez l'onglet `IA optionnelle`.
2. Activez l'IA seulement si vous voulez ajouter des syntheses automatiques.
3. Choisissez le fournisseur : OpenAI, OpenRouter, Groq, Mistral compatible ou Custom.
4. Renseignez `AI_API_KEY`, `AI_MODEL` et, pour un fournisseur custom, `AI_BASE_URL`.
5. Cliquez sur `Tester la configuration IA`.

Si l'IA n'est pas configuree, la veille fonctionne normalement sans synthese IA.

### Secrets GitHub depuis l'interface

L'onglet `Mise en route` affiche la liste des secrets a creer dans GitHub Actions.

L'interface ne les envoie pas automatiquement a GitHub. Il faut les ajouter manuellement dans :

`Settings` > `Secrets and variables` > `Actions`

Secrets SMTP obligatoires :

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `MAIL_FROM`

Secrets IA optionnels :

- `AI_PROVIDER`
- `AI_API_KEY`
- `AI_MODEL`
- `AI_BASE_URL`

## Changer la frequence

La frequence se modifie dans `.github/workflows/veille.yml`.

Par defaut, la veille se lance chaque lundi matin :

```yaml
schedule:
  - cron: "0 7 * * 1"
```

Exemples :

- Tous les jours a 7h : `0 7 * * *`
- Tous les mercredis a 8h : `0 8 * * 3`
- Le 1er du mois a 9h : `0 9 1 * *`

Les horaires GitHub Actions sont en UTC.

## Utilisation sans IA

C'est le fonctionnement par defaut.

Ne renseignez pas `AI_PROVIDER` et `AI_API_KEY`. Le mail contiendra les informations detectees dans les flux, sans synthese automatique.

## Utilisation avec IA optionnelle

Si une IA est configuree, elle ajoute une synthese courte pour les premiers resultats :

- Resume ;
- Interet pour une association ou un ALSH ;
- Public concerne ;
- Niveau d'attention : faible, moyen ou fort ;
- Action conseillee.

Fournisseurs compatibles OpenAI pris en charge :

| Fournisseur | `AI_PROVIDER` | `AI_BASE_URL` |
| --- | --- | --- |
| OpenAI | `openai` | Peut etre laisse vide |
| OpenRouter | `openrouter` | Peut etre laisse vide |
| Groq | `groq` | Peut etre laisse vide |
| Mistral compatible OpenAI | `mistral` | Peut etre laisse vide |
| Fournisseur compatible custom | `custom` | Obligatoire |

Exemples :

```env
AI_PROVIDER=openrouter
AI_API_KEY=sk-...
AI_MODEL=openai/gpt-4o-mini
AI_BASE_URL=
```

```env
AI_PROVIDER=custom
AI_API_KEY=...
AI_MODEL=mon-modele
AI_BASE_URL=https://mon-fournisseur.example/v1
```

L'architecture prevoit des classes dediees pour ajouter plus tard Anthropic ou Gemini. Si une erreur IA survient, l'outil continue et envoie la veille sans synthese pour l'element concerne.

## Reglages utiles

Les reglages principaux sont dans `config/settings.yml` :

- objet du mail ;
- introduction ;
- nombre maximum d'elements par envoi ;
- envoi ou non d'un mail vide ;
- activation des elements sans categorie ;
- nombre maximum de syntheses IA ;
- mention de prudence juridique.

## Suivi des doublons

Le fichier `data/seen_items.json` contient les elements deja vus.

Le workflow GitHub Actions le met a jour apres chaque execution et le commit automatiquement si le fichier a change. Cela evite de renvoyer les memes informations a chaque veille.

## Limites juridiques

Cette veille est une aide au repérage. Elle ne remplace pas une analyse juridique, institutionnelle ou professionnelle.

Mention incluse dans chaque mail :

> Cette veille est générée automatiquement. Elle aide au repérage d’informations réglementaires et pédagogiques. Elle ne remplace pas une analyse juridique, institutionnelle ou professionnelle. Les décisions doivent être prises à partir des sources officielles.

## Depannage

### Aucun mail n'arrive

- Verifiez les secrets SMTP dans GitHub.
- Verifiez que votre fournisseur mail autorise l'envoi SMTP.
- Utilisez un mot de passe d'application si votre messagerie l'exige.
- Verifiez les destinataires dans `config/recipients.yml`.

### La veille ne trouve rien

- Verifiez que les flux dans `config/sources.yml` sont accessibles.
- Ajoutez des mots-cles dans `config/categories.yml`.
- Mettez temporairement `include_uncategorized: true` dans `config/settings.yml`.

### Les memes elements reviennent

- Verifiez que `data/seen_items.json` est bien commit apres le workflow.
- Verifiez que le workflow a la permission `contents: write`.

### L'IA ne s'affiche pas

- Verifiez `AI_PROVIDER`, `AI_API_KEY` et `AI_MODEL`.
- Pour `custom`, verifiez aussi `AI_BASE_URL`.
- Consultez les logs GitHub Actions : une erreur IA ne bloque pas la veille.

### Tester sans envoyer

Lancez :

```bash
python src/main.py --dry-run
```

Cela permet de verifier les sources, les categories et le rendu general sans envoyer de mail.
