#!/usr/bin/env bash
# Lance le tableau de ce projet. Le moteur est dashboard-moteur/, à côté de ce script.
# Le dossier courant n'est pas changé.

set -euo pipefail

source="${BASH_SOURCE[0]}"
while [ -L "$source" ]; do
  dir="$(cd "$(dirname "$source")" && pwd)"
  source="$(readlink "$source")"
  if [[ "$source" != /* ]]; then
    source="$dir/$source"
  fi
done
root="$(cd "$(dirname "$source")/.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "erreur : python3 introuvable" >&2
  exit 1
fi

engine="$root/dashboard-moteur/server.py"
motor="$root/dashboard-moteur"
if [ -e "$engine" ]; then
  resolved_engine="$(readlink -f -- "$engine")"
  resolved_dir="$(readlink -f -- "$motor")"
  case "$resolved_engine" in
    "$resolved_dir"/*)
      if [ -f "$resolved_engine" ]; then
        exec python3 -u "$resolved_engine" "$@"
      fi
      ;;
  esac
fi

echo "erreur : moteur local introuvable" >&2
exit 1
