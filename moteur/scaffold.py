"""Crée le socle d'un projet. N'écrase pas un fichier déjà là."""

from __future__ import annotations

from pathlib import Path

ENGINE = Path(__file__).resolve().parent
MODEL = ENGINE.parent / "modele"
FILES = ("dashboard.toml", "DECISIONS.md")


class InitError(ValueError):
    pass


def init_project(root: Path) -> list[str]:
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
        src = MODEL / name
        try:
            text = src.read_text(encoding="utf-8")
        except OSError as exc:
            raise InitError("modèle illisible") from exc
        if "/home/" in text or '="/' in text or "='/" in text:
            raise InitError("modèle refusé")
        try:
            dest.write_text(text, encoding="utf-8")
        except OSError as exc:
            raise InitError("écriture impossible") from exc
        created.append(name)
    return created
