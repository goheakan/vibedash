"""Registre local des projets ouverts.

Les chemins restent dans ce fichier (hors du dépôt). L'API ne reçoit qu'un
identifiant et le nom lu dans dashboard.toml.
"""

from __future__ import annotations

import json
import os
import re
import threading
import unicodedata
from pathlib import Path

from parse import ParseError, load

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_HOME_PATH = re.compile(r"/(?:home|root|Users|tmp)/")


class RegistryError(ValueError):
    pass


def public_message(msg: str) -> str:
    text = str(msg or "").strip()
    if not text or len(text) > 200 or "\n" in text or _HOME_PATH.search(text):
        return "lecture impossible"
    return text


def slug(name: str) -> str:
    norm = unicodedata.normalize("NFKD", name or "")
    ascii_name = norm.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    return text or "projet"


def fresh_id(folder_name: str, taken: set[str]) -> str:
    base = slug(folder_name)
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def default_registry_path() -> Path:
    override = os.environ.get("DASHBOARD_REGISTRY", "").strip()
    if override:
        path = Path(override).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        return path
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "dashboard-projet" / "projets.json"


class Registry:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()

    def open_path(self, raw: object, base: Path | None = None) -> dict:
        root = self._directory(raw, base or Path.cwd())
        with self._lock:
            data = self._read()
            found = next((item for item in data["projects"] if _same(item["path"], root)), None)
            if found:
                pid = found["id"]
            else:
                pid = fresh_id(root.name, {item["id"] for item in data["projects"]})
                data["projects"].append({"id": pid, "path": root.as_posix()})
            data["active"] = pid
            self._write(data)
        return self._card(pid, root)

    def close(self, pid: str) -> dict:
        self._require_id(pid)
        with self._lock:
            data = self._read()
            kept = [item for item in data["projects"] if item["id"] != pid]
            if len(kept) == len(data["projects"]):
                raise RegistryError("projet inconnu")
            data["projects"] = kept
            if data["active"] == pid:
                data["active"] = kept[0]["id"] if kept else ""
            self._write(data)
        return self.snapshot()

    def activate(self, pid: str) -> dict:
        self._require_id(pid)
        with self._lock:
            data = self._read()
            if not any(item["id"] == pid for item in data["projects"]):
                raise RegistryError("projet inconnu")
            data["active"] = pid
            self._write(data)
        return self.snapshot()

    def path_of(self, pid: str) -> Path:
        self._require_id(pid)
        with self._lock:
            data = self._read()
            for item in data["projects"]:
                if item["id"] == pid:
                    return Path(item["path"])
        raise RegistryError("projet inconnu")

    def snapshot(self) -> dict:
        with self._lock:
            data = self._read()
            items = list(data["projects"])
            active = data["active"]
        projects = [self._public_item(item) for item in items]
        ids = [item["id"] for item in projects]
        if active not in ids:
            active = ids[0] if ids else ""
        return {"active": active, "projects": projects}

    def _require_id(self, pid: str) -> None:
        if not isinstance(pid, str) or not ID_RE.fullmatch(pid):
            raise RegistryError("projet inconnu")

    def _directory(self, raw: object, base: Path) -> Path:
        if not isinstance(raw, str):
            raise RegistryError("chemin attendu")
        text = raw.strip()
        if not text:
            raise RegistryError("chemin vide")
        if "\x00" in text or "\n" in text or "\r" in text or len(text) > 4096:
            raise RegistryError("chemin refusé")
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = base / path
        try:
            root = path.resolve(strict=True)
        except OSError as exc:
            raise RegistryError("dossier introuvable") from exc
        if not root.is_dir():
            raise RegistryError("ce n'est pas un dossier")
        toml = root / "dashboard.toml"
        if toml.is_symlink():
            try:
                target = toml.resolve(strict=True)
            except OSError as exc:
                raise RegistryError("dashboard.toml absent") from exc
            if root not in target.parents:
                raise RegistryError("dashboard.toml hors du projet")
        if not toml.is_file():
            raise RegistryError("dashboard.toml absent")
        try:
            load(root)
        except ParseError as exc:
            raise RegistryError(public_message(str(exc))) from exc
        return root

    def _public_item(self, item: dict) -> dict:
        root = Path(item["path"])
        toml = root / "dashboard.toml"
        if not root.is_dir() or not toml.is_file():
            return {
                "id": item["id"],
                "name": item["id"],
                "tagline": "",
                "pending": 0,
                "error": "projet introuvable",
            }
        return self._card(item["id"], root)

    def _card(self, pid: str, root: Path) -> dict:
        try:
            state = load(root)
        except ParseError as exc:
            return {
                "id": pid,
                "name": pid,
                "tagline": "",
                "pending": 0,
                "error": public_message(str(exc)),
            }
        return {
            "id": pid,
            "name": state["project"]["name"],
            "tagline": state["project"]["tagline"],
            "pending": int(state["stats"]["pending"]),
        }

    def _read(self) -> dict:
        if not self.path.is_file():
            return {"active": "", "projects": []}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryError("registre illisible") from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("projects"), list):
            raise RegistryError("registre illisible")
        projects = []
        for item in raw["projects"]:
            if not isinstance(item, dict):
                continue
            pid = item.get("id")
            path = item.get("path")
            if isinstance(pid, str) and isinstance(path, str) and ID_RE.fullmatch(pid):
                projects.append({"id": pid, "path": path})
        active = raw.get("active")
        if not isinstance(active, str):
            active = ""
        return {"active": active, "projects": projects}

    def _write(self, data: dict) -> None:
        parent = self.path.parent
        parent.mkdir(parents=True, exist_ok=True)
        if parent.name == "dashboard-projet":
            os.chmod(parent, 0o700)
        payload = json.dumps(
            {"active": data["active"], "projects": data["projects"]},
            ensure_ascii=False,
            indent=2,
        )
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(payload + "\n", encoding="utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)
        os.chmod(self.path, 0o600)


def _same(stored: str, root: Path) -> bool:
    try:
        return Path(stored).resolve() == root
    except OSError:
        return Path(stored).as_posix() == root.as_posix()
