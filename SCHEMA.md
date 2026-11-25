# Schéma — tableau de bord

Date : 2026-11-10.

Fichiers à la **racine du projet suivi**, pas dans ce dépôt. Modèle prêt à copier : `modele/`.

`bin/dashboard init`, lancé dans le dossier du projet, copie `dashboard.toml` et `DECISIONS.md` seulement s'ils manquent. `init --vendor` copie aussi le moteur dans `dashboard-moteur/` (sans les tests) et écrit `scripts/dashboard.sh`. Un fichier déjà présent n'est pas écrasé. `bin/dashboard serve` ouvre ensuite ce dossier. Sans sous-commande, `bin/dashboard` fait de même si `dashboard.toml` est déjà là. Un `dashboard-moteur/server.py` n'est lancé que s'il reste dans ce dossier.

## dashboard.toml

À la racine du projet. Champs utiles :

```toml
name = "Nom"
tagline = "Une phrase"
identity = "Auteur public"
locale = "fr"
host = "127.0.0.1"
port = 3847

[sources]
decisions = "DECISIONS.md"
plan = "../PLAN.md"          # optionnel
jalon_glob = "J*.md"

[[milestones]]
id = "J0"
title = "Titre du jalon"

[[constraints]]
text = "Règle visible en tête."

[lanes.sales]
title = "Vente"
decision_ids = ["D10", "D11"]

[[extras]]
id = "PLAY"
title = "Publication"
lane = "sales"
summary = "…"
from_jalon = "J10"           # statut calqué sur ce jalon
```

Le serveur **force** `127.0.0.1` même si le toml dit autre chose. Le champ `port` reste lu, mais le tableau n'écoute que `--port` (défaut 3847), une fois pour tous les projets ouverts.

## DECISIONS.md

Tableau obligatoire :

```markdown
| ID | Statut | Date | Choix |
|---|---|---|---|
| D1 | **tranché** | 2026-11-09 | le choix |
| D2 | en attente | | reco : … |
| D3 | orientation | 2026-11-09 | direction, pas encore figé |
```

Puis une section par ID :

```markdown
## D1 — Titre court

Texte libre. C’est ce qui s’ouvre dans le panneau.
```

Statuts reconnus : `tranché` (et variantes), `en attente`, `orientation`.

## Jalons

- Catalogue : `[[milestones]]` dans le toml, ou titres `### J0 — …` dans le plan.
- Preuve : fichier `J0.md` à la racine = **fait**.

## Sortie JSON

`python3 moteur/server.py --project . --dump`  
Aucun chemin `/home/…` dans la charge utile.

## Plusieurs projets

`python3 moteur/server.py` sert tous les projets ouverts sur une seule adresse. Chacun est un onglet. Le JSON (`/api/projects`, `/api/state`) porte un identifiant et le nom lu dans le toml, pas le chemin du dossier. Les chemins restent dans le registre local, hors du dépôt.
