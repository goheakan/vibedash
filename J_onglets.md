# Onglets — plusieurs projets, un tableau

Date : 2026-11-13.

## Fait

- Un serveur sur `127.0.0.1`, port `--port` ou 3847.
- Ouvrir un dossier qui a déjà un `dashboard.toml`. Rien n'est écrit dedans.
- Un onglet par projet. Changer d'onglet change les décisions et les jalons affichés.
- Retirer un onglet retire le dossier du registre. Les fichiers du projet restent.
- Le même dossier ouvert deux fois reste un seul onglet.
- Un `dashboard.toml` qui est un lien vers l'extérieur du projet est refusé.
- Le JSON servi ne contient pas le chemin du dossier.
- Registre : `$XDG_CONFIG_HOME/dashboard-projet/projets.json`, mode `0600`. Surcharge : `DASHBOARD_REGISTRY` ou `--registry`.

## Rapport de vérification

```
RAPPORT DE VÉRIFICATION
Build     : OK
Types     : OK (0 erreur, pyright sur moteur/ et moteur/tests/)
Lint      : OK (0, ruff check moteur)
Tests     : OK (23/23, couverture non mesurée : le module coverage est absent)
Sécurité  : OK (0 problème dans les fichiers relus ; gitleaks absent)
Diff      : pas de dépôt git, 16 fichiers écrits ou modifiés
Global    : PRÊT pour ce jalon
Cible     : VÉRIFIÉE (Chromium /usr/bin/chromium, headless, Playwright)
Prochaine étape permise : utiliser le tableau, ou un go écrit pour J0 / J1
À corriger : aucun pour ce jalon
```

Cible, le 2026-11-13. Page réelle dans Chromium headless, pas seulement l'API.

- Bureau 1280×800 : tableau vide, ouverture d'un projet, second projet avec la touche `o`, retour au premier onglet, le texte de l'autre projet n'est plus dans la page.
- Chemin absent : message « dossier introuvable », le chemin n'est pas répété.
- Mobile 390×844 : la barre d'onglets tient dans la largeur, le second onglet affiche son propre texte.
- Retrait de l'onglet : le fichier `DECISIONS.md` du projet est encore là.
- Aucune requête vers un autre hôte que `127.0.0.1`.

## Reste

La commande `init` et le kit à copier dans un projet. Voir `PLAN_GROK_BUILD.md`.
