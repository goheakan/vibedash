"""Crée le socle d'un projet. N'écrase pas un fichier déjà là."""

from __future__ import annotations

import shutil
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
MODEL = ENGINE.parent / "modele"
FILES = ("dashboard.toml", "DECISIONS.md")
LAUNCHER = MODEL / "dashboard.sh"


class InitError(ValueError):
    pass


def init_project(root: Path, vendor: bool = False) -> list[str]:
    if not isinstance(root, Path):
        raise InitError("dossier attendu")
    try:
        folder = root.resolve(strict=True)
    except OSError as exc:
        raise InitError("dossier introuvable") from exc
    if not folder.is_dir():
        raise InitError("ce n'est pas un dossier")
    created: list[str] = []
    for name in FILES:
        dest = folder / name
        if dest.exists() or dest.is_symlink():
            continue
        created.append(_write_model(dest, MODEL / name))
    if vendor:
        created.extend(_vendor_kit(folder))
    return created


def _write_model(dest: Path, src: Path) -> str:
    try:
        text = src.read_text(encoding="utf-8")
    except OSError as exc:
        raise InitError("modèle illisible") from exc
    if "/home/" in text or "Grok_Build" in text or '="/' in text or "='/" in text:
        raise InitError("modèle refusé")
    try:
        dest.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise InitError("écriture impossible") from exc
    return dest.name


def _vendor_kit(folder: Path) -> list[str]:
    created: list[str] = []
    motor = folder / "dashboard-moteur"
    if not motor.exists() and not motor.is_symlink():
        try:
            shutil.copytree(
                ENGINE,
                motor,
                ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc", "*.pyo"),
                symlinks=False,
            )
        except OSError as exc:
            raise InitError("écriture impossible") from exc
        created.append("dashboard-moteur/")
    scripts = folder / "scripts"
    script = scripts / "dashboard.sh"
    if scripts.is_symlink() or script.exists() or script.is_symlink():
        return created
    try:
        scripts.mkdir(exist_ok=True)
    except OSError as exc:
        raise InitError("écriture impossible") from exc
    _write_model(script, LAUNCHER)
    try:
        script.chmod(0o755)
    except OSError as exc:
        raise InitError("écriture impossible") from exc
    created.append("scripts/dashboard.sh")
    return created
