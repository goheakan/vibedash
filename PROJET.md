# VibeDash — persistance

Date : 2026-11-13.

Outil local pour voir les décisions prises ou restantes, les jalons, et la vente. Réutilisable. Privacy-first, self-host / 127.0.0.1, FLOSS, pas de SaaS.

## Où on en est

Le moteur sert **plusieurs projets déjà créés** dans un seul tableau : un processus, un port, un onglet par projet. Décision D5, tranchée. Détail et rapport : `J_onglets.md`, `DECISIONS.md`.

Lancer : `./bin/dashboard`, puis **Ouvrir** (touche `o`) avec le dossier qui contient `dashboard.toml`. Le script transmet les arguments à `moteur/server.py`. Le moteur reste Python (D6). Les chemins restent dans le registre local (`$XDG_CONFIG_HOME/dashboard-projet/projets.json`, sinon `~/.config/dashboard-projet/projets.json`). Retirer un onglet ne supprime pas les fichiers. Le Markdown de chaque projet reste la source.

J0 est fait. J1 est fait : `bin/dashboard init` crée `dashboard.toml` et `DECISIONS.md` sans les écraser, `bin/dashboard serve` ouvre le dossier courant. Compte rendu : `J1.md`. La suite attend un go J2. Ensuite : le durcissement de `serve` (J2), le kit autonome (J3), les vérifs de J4.

## Ce que ce dossier contient

| Chemin | Rôle |
|---|---|
| `PLAN_GROK_BUILD.md` | Feuille d'instructions |
| `bin/dashboard` | Script bash qui lance le moteur |
| `DECISIONS.md` | D1, D2, D4, D5, D6 et D7 tranchées |
| `J0.md` | Socle et rapport de vérification |
| `J1.md` | Init d'un projet et rapport de vérification |
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

Le symbole en service est `moteur/static/mark.png`, tiré de `logo-VD-vibedash.jpg`. Il est l'icône du navigateur et la marque dans la colonne. Le bandeau `moteur/static/lockup.png`, tiré de `VibeDash-horizontal.jpg`, est en tête des trois guides. Le damier des JPEG a été retiré. `moteur/static/icon.svg` reste le premier dessin, il n'est plus affiché.

Prompt du symbole :

```
Reprends cette icône telle quelle et ne change que les lettres. Garde le carré #161920, les coins arrondis, la grille de deux par deux, les marges et l'intervalle. Garde les quatre tuiles : haut gauche #e0b36a opaque, haut droite #7cbc8e à 90 %, bas gauche #7ba3d4 à 90 %, bas droite #ece8e1 à 25 %. Aucun dégradé, aucune ombre, aucun relief, aucun contour.

Ajoute deux capitales dessinées pour cette marque, sans géométrique, graisse moyenne, même hauteur. Un V centré dans la tuile or, en #ece8e1. Un D centré dans la tuile blanche, en #e0b36a. Les deux lettres reposent sur la même ligne, avec de l'air autour d'elles, sans toucher le bord de leur tuile. Les tuiles bleue et claire restent vides. Aucun autre texte, aucun mot, aucun symbole.
```

Prompt du bandeau :

```
Composition horizontale, fond transparent, style d'identité d'un outil professionnel. À gauche, le symbole fourni, inchangé : carré arrondi #161920, quatre tuiles, V en #ece8e1 sur #e0b36a, D en #e0b36a sur #ece8e1, tuile #7cbc8e et tuile #7ba3d4 à 25 % sans lettre. À droite, sur la même ligne médiane, le nom VibeDash. Une seule ligne, même sans géométrique que le V et le D, couleur #ece8e1, casses V et D capitales, le reste en bas de casse. Espace large et régulier entre le symbole et le nom. Aucun slogan, aucune ombre, aucun relief, aucun dégradé, aucun fond texturé, aucun autre mot.
```

## Hors périmètre

- Ne pas ouvrir le dashboard sur le réseau local
- Ne pas allumer Docker « pour voir »
- Ne pas modifier un projet existant (dont une app Android) sans OK écrit
- Aucun commit sans demande

## Suite

Le tableau multi-projets est utilisable. J1 est rendu. Le jalon suivant (J2, `serve` sans chemin cassé) attend un go J2 écrit.
