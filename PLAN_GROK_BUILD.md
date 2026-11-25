# Plan Grok Build — Dashboard de projet

Date : 2026-11-10 (Europe/Paris)  
Destinataire : **Grok Build** (nouvelle session, ouverte dans ce dossier).  
Validation : **OK écrit de l’éditeur** pour tout checkpoint ⛔.

> Feuille d’instructions. Exécuter les jalons **dans l’ordre**. Ne pas cocher un critère sans commande ou test. Ce dossier est **autonome** : tout ce qu’il faut est ici. Ne pas aller chercher le contexte dans une autre session.

---

## 0. Règles dures (à relire avant chaque session)

1. **Pas de sudo**. Si une commande en a besoin, l’écrire et demander à l’éditeur de la lancer.
2. **Ne jamais ouvrir** `.env`, `*.env`, `auth.json`, clés, keystores, `wp-config.php`. Ne jamais afficher ni logguer un secret.
3. **Aucune donnée personnelle** dans les fichiers : pas de prénom réel, pas de chemin `/home/…`, pas d’e-mail perso.
4. **127.0.0.1 seulement.** Jamais `0.0.0.0`, jamais une écoute sur le réseau local. Le Wi-Fi de la maison n’est pas une zone de confiance.
5. **Pas de Docker**, pas de compte, pas de SaaS, pas de CDN, pas de police web distante. Python **stdlib** (3.11+) sauf OK écrit pour une dépendance.
6. **Markdown = source de vérité.** Le HTML ne fait que lire `DECISIONS.md`, `J*.md`, `dashboard.toml`. Pas de seconde base.
7. **Ne pas modifier d’autres projets** (apps, sites, labo) sans OK écrit. Le premier usage réel pourra servir de cible **après** le checkpoint.
8. **Aucun commit** sans demande explicite.
9. Répondre en **français**. Chemins **relatifs** dans les docs.
10. Persistance : tenir `PROJET.md` à jour au fil des jalons.

---

## 1. But

Un tableau de bord **facilement déployable sur n’importe quel projet** :

- l’éditeur entre dans un dossier de projet ;
- une commande (ou un petit script copié) ouvre `http://127.0.0.1:<port>` ;
- les décisions / jalons / vente de **ce** projet s’affichent ;
- aucun chemin magique vers `Documents/Grok_Build/…` n’est exigé une fois déployé.

Public : l’éditeur, solo, plusieurs projets. Pas une équipe, pas un cloud.

---

## 2. État du prototype (déjà là)

Code dans `moteur/` :

| Fichier | Rôle |
|---|---|
| `parse.py` | Lit `dashboard.toml` + tableau `DECISIONS.md` + `J*.md` |
| `server.py` | HTTP `127.0.0.1`, `/api/state`, fichiers `static/` |
| `static/` | UI (triage, clavier, jalons, vente) |
| `tests/` | unittest + fixture générique |

Contrat des fichiers projet : `SCHEMA.md`. Squelette à copier : `modele/`.

Lancer le prototype sur un projet qui a déjà un `dashboard.toml` :

```bash
python3 moteur/server.py --project ../chemin/vers/projet
python3 -m unittest discover -s moteur/tests -v
```

Limite actuelle : il faut connaître l’emplacement de `moteur/` et passer `--project`. Un projet ne s’initialise pas tout seul. Un lanceur existant ailleurs pointe vers une **autre** copie du prototype : cette copie-là ne doit plus être enrichie. **Ici** est le canon.

---

## 3. UX à conserver

Ce que les utilisateurs d’autres dashboards ont salué, déjà dans `static/` :

| Source | À garder |
|---|---|
| Linear | Vitesse, liste dense, triage (à trancher d’abord), clavier (`/`, `g i/d/j/v`, `j/k`), cycles = jalons |
| Leantime | Écran **Maintenant**, but du projet visible, moins de fatigue |
| Kanban | Trois colonnes de jalons |
| Notion / fichiers | Détail en panneau, Markdown maître |

Ne pas ajouter de SaaS, de kanban lourd, ni de CRM. La vente = cartes issues des décisions + extras du toml.

---

## 4. Décisions à trancher (éditeur)

Les consigner dans un `DECISIONS.md` **de ce dossier** (le dashboard du dashboard), dès J0.

| ID | Question | Reco |
|---|---|---|
| **D1** | Forme du déploiement | **Tranchée le 2026-11-13, go J0.** (b) un moteur unique dans ce dépôt. `init` / `serve` sur le dossier courant : J1 et J2. `init --vendor` : J3. |
| **D2** | Nom de la commande | **Tranchée le 2026-11-25.** `bin/vibedash`, script bash. `./install.sh` pose un lien dans `~/.local/bin`. Pas de `sudo`, pas d'install système. |
| **D3** | Ports | 3847 par défaut. Si le port est pris : le dire. Pas de port suivant automatique. |
| **D5** | Plusieurs projets en même temps | **Tranchée le 2026-11-13.** Un processus, un port, un onglet par projet. Registre des chemins hors du dépôt. Le `port` d'un `dashboard.toml` n'est pas écouté. Voir `DECISIONS.md`. |
| **D4** | Licence de **cet** outil | **Tranchée le 2026-11-13.** MIT, comme `vb-optifree`. |

---

## 5. Jalons

### J0 — Socle de ce dépôt

- Relire §0. Créer `DECISIONS.md` ici (D1–D4 en attente).
- Remplir `grok_session.sh` avec `grok -r <ID>` de **cette** session.
- `python3 -m unittest discover -s moteur/tests -v` vert.
- ⛔ **CHECKPOINT** : D1 et D2 tranchés (D3–D4 peuvent attendre J2).

### J1 — Init d’un projet

Fait le 2026-11-13, en attente de validation. Voir `J1.md`.

- Commande unique, depuis **n’importe quel** dossier projet :

  ```bash
  /chemin/vers/ce/dépôt/bin/vibedash init
  # ou vibedash init, après ./install.sh
  ```

- Crée `dashboard.toml` et `DECISIONS.md` **seulement s’ils n’existent pas** (ne pas écraser).
- Chemins dans le toml : relatifs au projet, jamais un home.
- **Terminé quand** : un dossier temporaire vide, `init`, puis `serve`, page 127.0.0.1 avec le nom du projet. Test automatisé (unittest ou script).

### J2 — Serve sans chemin cassé

Fait le 2026-11-25, en attente de validation. Voir `J2.md`.

- `serve` (défaut) : cwd = projet, moteur = ce dépôt **ou** `./dashboard-moteur/` vendored.
- Bind forcé `127.0.0.1`.
- `--dump` conserve le JSON sans `/home/…`.
- D5 couvre le travail simultané : un tableau, deux projets, deux onglets, un port. Deux `serve` en parallèle ne sont plus le critère.
- **Terminé quand** : `init` + `serve` documentés dans `README.md` ; tests verts ; `PROJET.md` à jour.

### J3 — Kit autonome (option D1)

Fait le 2026-11-25, en attente de validation. Voir `J3.md`.

- `init --vendor` copie `moteur/` (sans tests, sans `__pycache__`) dans le projet, plus un `scripts/dashboard.sh` **relatif** qui n’a plus besoin de `Documents/Grok_Build`.
- **Terminé quand** : on peut `cp -a` ce kit dans un autre arbre et servir sans ce dépôt.

### J4 — Vérifs et cibles

Fait le 2026-11-25, en attente de validation. Voir `J4.md`.

- Tests parseur + au moins un parcours HTTP (`/api/state` contient les D* du modèle).
- CSP déjà dans `index.html` : la garder.
- Documenter le clavier dans `README.md`.
- ⛔ **CHECKPOINT** : OK pour brancher un projet réel existant (l’éditeur nomme lequel). Jusque-là, seulement des dossiers de test.

---

## 6. Hors sujet (ne pas faire)

- Notion, Linear, AppFlowy, Kanboard, Docker, Plane, Twenty.
- Ouvrir un port « pour le téléphone » ou le LAN.
- Lire ou modifier des apps, sites, labos, sans OK.
- Polices Google, analytics, service worker qui appelle le réseau.

---

## 7. Livrable de fin de session

À chaque arrêt : `PROJET.md` daté (fait / reste / commandes de vérif) + tests lancés. Pas de « ça devrait marcher ».
