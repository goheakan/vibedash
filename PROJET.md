# VibeDash — persistance

Date : 2026-11-13.

Outil local pour voir les décisions prises ou restantes, les jalons, et la vente. Réutilisable. Privacy-first, self-host / 127.0.0.1, FLOSS, pas de SaaS.

## Où on en est

Le moteur sert **plusieurs projets déjà créés** dans un seul tableau : un processus, un port, un onglet par projet. Décision D5, tranchée. Détail et rapport : `J_onglets.md`, `DECISIONS.md`.

Lancer : `./bin/dashboard`, puis **Ouvrir** (touche `o`) avec le dossier qui contient `dashboard.toml`. Le script transmet les arguments à `moteur/server.py`. Le moteur reste Python (D6). Les chemins restent dans le registre local (`$XDG_CONFIG_HOME/dashboard-projet/projets.json`, sinon `~/.config/dashboard-projet/projets.json`). Retirer un onglet ne supprime pas les fichiers. Le Markdown de chaque projet reste la source.

Ce qui manque encore, dans l'ordre du plan : J0 (D1), puis `init` / `serve` (J1–J2), le kit autonome (J3), les vérifs de J4. D2 et D6 sont tranchées. J2 ne demande plus deux serveurs en parallèle.

## Ce que ce dossier contient

| Chemin | Rôle |
|---|---|
| `PLAN_GROK_BUILD.md` | Feuille d'instructions |
| `bin/dashboard` | Script bash qui lance le moteur |
| `DECISIONS.md` | D2, D4, D5, D6 et D7 tranchées. D1 ouverte |
| `J_onglets.md` | Jalon onglets et rapport de vérification |
| `SCHEMA.md` | Contrat `dashboard.toml` + `DECISIONS.md` |
| `moteur/` | Parseur, registre, serveur, HTML |
| `modele/` | Fichiers à déposer dans un projet vierge |
| `grok_session.sh` | Ouvrir / reprendre la session de ce dossier |

Rien d'un autre projet (pas d'app, pas de secrets, pas de chemins personnels).

## Sécurité git

Publication du 2026-11-13, dépôt `goheakan/vibedash`. `git` est en `2.56.1` (relu ce jour-là). `gitleaks` n'est pas installé : relecture manuelle, pas de secret, pas d'adresse de réseau, pas de chemin personnel. `projets.json` et `grok_session.sh` sont ignorés. Le registre par défaut est hors de l'arbre.

- Le dossier n'est pas le home.
- Pas de `.gitmodules`. Remote HTTPS `https://github.com/goheakan/vibedash.git`, sans jeton dans l'URL. Même méthode que les dépôts OpenCode qui poussent déjà. `credential.helper` reste `libsecret`.
- `~/.gitconfig` n'est pas modifié. L'identité locale du dépôt est `goheakan` avec l'adresse noreply GitHub. Pas de hook activé.
- `git status` est lu avant `git add`. Les chemins sont nommés.
- La racine Git n'est pas servie : le serveur ne rend que `moteur/static` et l'API.
- Licence MIT (D4), le même texte que `vb-optifree`.

## Logo

Le dessin actuel de `moteur/static/icon.svg` reste : carré sombre, quatre tuiles. Prompt pour Grok Imagine, si une version plus finie est voulue plus tard :

```
Icône d'application carrée, plate, professionnelle, sur fond transparent. Un carré presque plein cadre, fond #161920, coins arrondis d'environ un cinquième du côté. Dedans, une grille de deux par deux, marges égales, intervalle étroit. Chaque tuile a des coins légèrement arrondis. Haut gauche : #e0b36a, opaque. Haut droite : #7cbc8e à 90 % d'opacité. Bas gauche : #7ba3d4 à 90 % d'opacité. Bas droite : #ece8e1 à 25 % d'opacité, un souffle clair sur le fond sombre. Aucun texte, aucune lettre, aucun dégradé, aucune ombre, aucun relief, aucun contour blanc, aucun autre symbole. Rendu net, vectoriel, calme, marque d'outil de bureau.
```

## Hors périmètre

- Ne pas ouvrir le dashboard sur le réseau local
- Ne pas allumer Docker « pour voir »
- Ne pas modifier un projet existant (dont une app Android) sans OK écrit
- Aucun commit sans demande

## Suite

Le tableau multi-projets est utilisable. Le jalon suivant du plan (J0, puis la commande `init`) attend un go écrit.
