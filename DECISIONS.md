# Décisions — VibeDash

| ID | Statut | Date | Choix |
|---|---|---|---|
| D1 | **tranché** | 2026-11-13 | Un moteur unique dans ce dépôt. `init` et `serve` viendront sur le dossier courant |
| D2 | **tranché** | 2026-11-13 | La commande est `bin/dashboard`, un script bash |
| D4 | **tranché** | 2026-11-13 | MIT, le même texte que `vb-optifree` |
| D5 | **tranché** | 2026-11-13 | Un processus, un port, un onglet par projet |
| D6 | **tranché** | 2026-11-13 | Le moteur reste Python. Pas de réécriture Rust |
| D7 | **tranché** | 2026-11-13 | Nom public VibeDash, dépôt `goheakan/vibedash` |

D3 est couverte par D5 : un port, 3847 par défaut. Si ce port est pris, le programme le dit et s'arrête.

## D1 — Déploiement

Forme (b) du plan, tranchée avec le go J0. Un seul moteur, celui de ce dépôt. `bin/dashboard` le lance. `init` et `serve` agissent sur le dossier courant (J1). `init --vendor`, le kit autonome, reste J3.

## D4 — Licence

MIT, comme `vb-optifree`. `yt-word-search` est en AGPL-3.0-or-later : ce n'est pas le modèle retenu pour VibeDash. Le texte est `LICENSE`.

## D7 — Nom

VibeDash mélange vibe-coding et dashboard. Le dépôt public est `goheakan/vibedash`. Le registre local reste `dashboard-projet` : ce nom est déjà celui du dossier de configuration.

## D2 — Commande

`bin/dashboard` lance `moteur/server.py` et transmet les arguments. Il ne change pas le dossier courant. Il n'est pas copié dans `~/bin` ni installé sur le système.

## D6 — Python, pas Rust

Le tableau lit du Markdown et répond sur `127.0.0.1`. Les pannes utiles à empêcher sont un mauvais dossier, un chemin qui sort dans le JSON, ou une écoute autre que `127.0.0.1`. Elles sont déjà testées. Rust donnerait un binaire sans Python, pas un tableau plus sûr. Le moteur reste la bibliothèque standard de Python 3.11+.

## D5 — Plusieurs projets dans un tableau

Le tableau écoute une fois sur `127.0.0.1`. Chaque projet déjà créé s'ouvre dans un onglet. Le registre des chemins reste hors du dépôt : `$XDG_CONFIG_HOME/dashboard-projet/projets.json`, sinon `~/.config/dashboard-projet/projets.json`. On peut le déplacer avec `DASHBOARD_REGISTRY` ou `--registry`.

Retirer un onglet ne supprime pas les fichiers. Rouvrir le même dossier reprend le même onglet. Le Markdown de chaque projet reste la source des décisions et des jalons. Le champ `port` d'un `dashboard.toml` n'est pas écouté : le port du tableau est `--port`, sinon 3847.
