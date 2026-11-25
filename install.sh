#!/usr/bin/env bash
# Pose un lien vers bin/vibedash. Pas de copie du moteur, pas de droits d'administration.
# N'écrase pas un fichier déjà présent.

set -euo pipefail

source="${BASH_SOURCE[0]}"
while [ -L "$source" ]; do
  dir="$(cd "$(dirname "$source")" && pwd)"
  source="$(readlink "$source")"
  if [[ "$source" != /* ]]; then
    source="$dir/$source"
  fi
done
root="$(cd "$(dirname "$source")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "erreur : python3 introuvable" >&2
  exit 1
fi

target="$root/bin/vibedash"
if [ ! -f "$target" ]; then
  echo "erreur : commande introuvable" >&2
  exit 1
fi

if [ -n "${VIBEDASH_BIN_DIR:-}" ]; then
  dest_dir="$VIBEDASH_BIN_DIR"
else
  dest_dir="${HOME}/.local/bin"
fi

if [ -z "$dest_dir" ] || [ "$dest_dir" = "/" ]; then
  echo "erreur : dossier d'installation refusé" >&2
  exit 1
fi

if [ -L "$dest_dir" ]; then
  echo "erreur : le dossier d'installation est un lien" >&2
  exit 1
fi

mkdir -p -- "$dest_dir"
link="$dest_dir/vibedash"
wanted="$(readlink -f -- "$target")"

if [ -L "$link" ]; then
  current="$(readlink -f -- "$link")"
  if [ "$current" = "$wanted" ]; then
    echo "Déjà en place."
  else
    echo "erreur : vibedash existe et pointe ailleurs" >&2
    exit 1
  fi
elif [ -e "$link" ]; then
  echo "erreur : vibedash existe déjà" >&2
  exit 1
else
  ln -s -- "$target" "$link"
  echo "Installé."
fi

case ":${PATH}:" in
  *":${dest_dir}:"*)
    echo "La commande vibedash est disponible."
    ;;
  *)
    echo "Ajoute ce dossier au PATH pour lancer vibedash par son nom."
    echo "Fish : fish_add_path \"${dest_dir}\""
    ;;
esac
