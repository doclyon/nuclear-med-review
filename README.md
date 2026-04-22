# 🔬 nuclear-med-review

Revue quotidienne automatisée de la littérature scientifique en médecine
nucléaire. Exécution gratuite sur GitHub Actions (cron nocturne), génération
d'une page HTML structurée, envoi d'un email de notification avec HTML en
pièce jointe + archive web consultable sur GitHub Pages.

---

## Fonctionnement

Chaque nuit à **23:00 heure Martinique (03:00 UTC)**, le pipeline :

1. Interroge en parallèle **PubMed, RSS officiels, arXiv, medRxiv** (fenêtre 36h)
2. Déduplique (DOI/PMID strict + fuzzy match titre + mémoire 7 jours)
3. Score par mots-clés (strong = 2pts / context = 1pt, seuil = 2)
4. Envoie les candidats à **Claude Sonnet 4.6** qui classifie (10 rubriques),
   traduit le titre, résume en FR structuré (Contexte/Méthode/Résultats/
   Implication), attribue 1–3 ⭐
5. Génère un HTML responsive dark-mode avec sommaire cliquable
6. Publie sur `gh-pages` (archive web) + envoie un email avec top-3 et
   tableau des compteurs

---

## Déploiement — pas à pas

### 1. Créer le repo GitHub

```bash
cd nuclear-med-review
git init -b main
git add .
git commit -m "Initial commit"
# Créer un repo vide sur github.com puis :
git remote add origin https://github.com/<user>/nuclear-med-review.git
git push -u origin main
```

### 2. Obtenir les clés API

#### 🔑 Anthropic (Claude)
- Aller sur https://console.anthropic.com/settings/keys
- **Create Key** → nommer `nuclear-med-review`
- Copier la clé (format `sk-ant-…`) — visible une seule fois
- Créditer le compte (5–10 $ suffisent pour plusieurs mois)

#### 🔑 NCBI / PubMed
- Créer un compte sur https://www.ncbi.nlm.nih.gov/account/
- Aller dans **Account Settings → API Key Management → Create an API Key**
- Copier la clé (passe la limite de 3 → 10 req/s)

#### 🔑 Gmail App Password
Prérequis : **2FA activée** sur le compte Gmail.
- Aller sur https://myaccount.google.com/apppasswords
- Créer un mot de passe d'application → nom `nuclear-med-review`
- Copier les 16 caractères (avec les espaces)

### 3. Configurer les secrets GitHub

Dans ton repo : **Settings → Secrets and variables → Actions → New repository secret**

Ajoute ces 5 secrets :

| Nom | Valeur |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-…` |
| `PUBMED_API_KEY` | ta clé NCBI |
| `SMTP_USER` | `ton.email@gmail.com` |
| `SMTP_PASSWORD` | le mot de passe d'application Gmail (16 caractères) |
| `RECIPIENT_EMAIL` | ton email destinataire (souvent le même) |

Optionnel : `PUBLIC_ARCHIVE_URL` = `https://<user>.github.io/nuclear-med-review`

### 4. Activer GitHub Pages

- **Settings → Pages**
- Source : **Deploy from a branch**
- Branch : `gh-pages` / `/ (root)`
- Save

La branche `gh-pages` sera créée automatiquement au premier run réussi.
L'archive sera disponible à `https://<user>.github.io/nuclear-med-review`.

### 5. Premier test manuel

- **Actions** → **Daily Nuclear Medicine Review** → **Run workflow**
- Choisir `dry_run: true` pour un premier essai sans envoi d'email
- Vérifier les logs et l'artefact HTML téléchargeable
- Si OK, refaire un run avec `dry_run: false` → tu dois recevoir l'email

### 6. Vérifier le cron

Le cron est défini à `0 3 * * *` dans `.github/workflows/daily-review.yml`.
GitHub Actions exécute les crons avec un léger délai (généralement <15 min).
Vérifie les 2–3 premiers jours que le workflow se déclenche bien.

---

## Utilisation locale

### Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Éditer .env avec tes clés
```

### Commandes

```bash
# Mode démo (offline, articles synthétiques, génère output/review_YYYY-MM-DD.html)
python -m src.main --demo

# Dry-run (vrai fetch, pas d'email)
python -m src.main --dry-run --verbose

# Run complet
python -m src.main --verbose

# Tests unitaires
python tests/test_fetchers.py
python tests/test_processors.py
```

---

## Configuration

- `config/sources.yaml` — liste des journaux PubMed, flux RSS, catégories arXiv, sujets medRxiv
- `config/queries.yaml` — mots-clés de pertinence + seuil
- `config/categories.yaml` — les 10 rubriques de classement

Toute modification est rechargée au prochain run (pas de redéploiement).

---

## Coûts estimés

Volume typique : 30–60 articles/jour passés à Claude (après dédup et scoring).

| Poste | Détail | Coût/jour |
|---|---|---|
| Input tokens | ~800 tok/article × 50 = 40k | ~0,12 $ |
| Cache read (90 %) | Le system prompt est mis en cache | économie ~50 % |
| Output tokens | ~400 tok/article × 50 = 20k | ~0,30 $ |
| **Total Claude Sonnet 4.6** | | **~0,15–0,40 $/jour** |

Soit **5–12 $/mois** selon le volume. GitHub Actions gratuit (< 2 000 min/mois
sur repos publics, plus que nécessaire pour un run quotidien de ~3 min).

---

## Architecture

```
nuclear-med-review/
├── .github/workflows/daily-review.yml     # Cron quotidien
├── src/
│   ├── fetchers/          # PubMed, RSS, arXiv, medRxiv
│   ├── processors/        # Dedup, scoring, Claude
│   ├── renderer/          # Jinja2 -> HTML
│   ├── notifier/          # SMTP Gmail
│   ├── models.py          # Dataclass Article
│   ├── config.py          # Chargement YAML
│   ├── logging_setup.py   # Logging structuré
│   ├── demo_data.py       # Articles synthétiques pour --demo
│   └── main.py            # Orchestration
├── config/                # YAML de configuration
├── templates/review.html.j2
├── scripts/build_archive_index.py
├── tests/                 # Tests unitaires mockés
├── requirements.txt
├── .env.example
└── README.md
```

---

## Checklist de vérification post-déploiement

- [ ] Les 5 secrets sont créés (`ANTHROPIC_API_KEY`, `PUBMED_API_KEY`, `SMTP_USER`, `SMTP_PASSWORD`, `RECIPIENT_EMAIL`)
- [ ] Le premier `workflow_dispatch` en `dry_run: true` passe au vert
- [ ] L'artefact `review-<id>.zip` contient un `review_YYYY-MM-DD.html` non vide
- [ ] Le second run sans dry-run envoie bien un email
- [ ] L'email contient les top-3, le tableau des compteurs, la pièce jointe
- [ ] GitHub Pages sert `https://<user>.github.io/nuclear-med-review`
- [ ] Vérifier que le cron se déclenche automatiquement à J+1 (03:00 UTC)
- [ ] Après 2–3 jours : la mémoire 7 jours fonctionne (pas d'articles redondants)
- [ ] Optionnel : créer une règle de filtre Gmail pour marquer/ranger les revues

---

## Dépannage

**Le workflow échoue avec `ANTHROPIC_API_KEY absent`**
→ Vérifier que le secret est bien créé dans **Settings → Secrets and variables → Actions** (pas dans Environment secrets).

**L'email n'arrive pas**
→ Tester le login SMTP manuellement :
```python
import smtplib, ssl
smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context())
smtp.login("ton.email@gmail.com", "xxxx xxxx xxxx xxxx")
```
Si `Username and Password not accepted` : re-générer un App Password (la 2FA doit être active).

**PubMed renvoie 0 articles**
→ Normal si on lance un dimanche/lundi matin. PubMed indexe peu le week-end. La mémoire 7j rattrape la latence sur les jours suivants.

**L'archive gh-pages n'est pas créée**
→ Vérifier que `permissions: contents: write` est bien dans le workflow, et que la branche `gh-pages` n'est pas protégée.

---

## Licence

Projet personnel à usage du médecin qui l'a commandé. Libre adaptation.
