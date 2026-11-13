#!/usr/bin/env python3
"""Registre local : plusieurs projets, aucun chemin dans la vue publique."""

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from registry import Registry, RegistryError, default_registry_path, slug


def write_project(folder: Path, name: str, decision_id: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "dashboard.toml").write_text(
        f'name = "{name}"\nlocale = "fr"\n\n[sources]\ndecisions = "DECISIONS.md"\n',
        encoding="utf-8",
    )
    (folder / "DECISIONS.md").write_text(
        "\n".join(
            [
                f"# Décisions — {name}",
                "",
                "| ID | Statut | Date | Choix |",
                "|---|---|---|---|",
                f"| {decision_id} | en attente | | choix {name} |",
                "",
                f"## {decision_id} — Titre {name}",
                "",
                "Texte.",
                "",
            ]
        ),
        encoding="utf-8",
    )


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.reg = Registry(self.root / "reg.json")
        self.alpha = self.root / "alpha"
        self.beta = self.root / "beta"
        write_project(self.alpha, "Alpha", "D1")
        write_project(self.beta, "Beta", "D9")

    def tearDown(self):
        self.tmp.cleanup()

    def test_slug_ascii(self):
        self.assertEqual(slug("Mon Projet"), "mon-projet")
        self.assertEqual(slug("Été"), "ete")
        self.assertEqual(slug("..."), "projet")

    def test_open_two_projects_and_keep_paths_out_of_the_public_view(self):
        first = self.reg.open_path(str(self.alpha), self.root)
        second = self.reg.open_path(str(self.beta), self.root)
        self.assertEqual(first["id"], "alpha")
        self.assertEqual(first["name"], "Alpha")
        self.assertEqual(second["name"], "Beta")
        snap = self.reg.snapshot()
        self.assertEqual(snap["active"], "beta")
        self.assertEqual([p["id"] for p in snap["projects"]], ["alpha", "beta"])
        blob = json.dumps(snap)
        self.assertNotIn(str(self.alpha), blob)
        self.assertNotIn("/home/", blob)
        self.assertNotIn("path", blob)
        stored = json.loads((self.root / "reg.json").read_text(encoding="utf-8"))
        self.assertEqual(Path(stored["projects"][0]["path"]), self.alpha.resolve())

    def test_same_folder_is_idempotent(self):
        self.reg.open_path(str(self.alpha), self.root)
        again = self.reg.open_path(str(self.alpha), self.root)
        self.assertEqual(again["id"], "alpha")
        self.assertEqual(len(self.reg.snapshot()["projects"]), 1)

    def test_same_folder_name_gets_a_second_id(self):
        other = self.root / "nested" / "alpha"
        write_project(other, "Alpha bis", "D2")
        self.reg.open_path(str(self.alpha), self.root)
        card = self.reg.open_path(str(other), self.root)
        self.assertEqual(card["id"], "alpha-2")
        self.assertEqual(card["name"], "Alpha bis")

    def test_relative_path_uses_the_given_base(self):
        card = self.reg.open_path("alpha", self.root)
        self.assertEqual(card["name"], "Alpha")
        self.assertEqual(self.reg.path_of("alpha"), self.alpha.resolve())

    def test_refuse_missing_folder_file_and_toml(self):
        with self.assertRaises(RegistryError) as missing:
            self.reg.open_path(str(self.root / "absent"), self.root)
        self.assertEqual(str(missing.exception), "dossier introuvable")
        with self.assertRaises(RegistryError) as afile:
            self.reg.open_path(str(self.alpha / "DECISIONS.md"), self.root)
        self.assertEqual(str(afile.exception), "ce n'est pas un dossier")
        empty = self.root / "vide"
        empty.mkdir()
        with self.assertRaises(RegistryError) as notoml:
            self.reg.open_path(str(empty), self.root)
        self.assertEqual(str(notoml.exception), "dashboard.toml absent")
        self.assertFalse((self.root / "reg.json").exists())

    def test_refuse_empty_and_null(self):
        with self.assertRaises(RegistryError):
            self.reg.open_path("  ", self.root)
        with self.assertRaises(RegistryError):
            self.reg.open_path("alpha\x00", self.root)

    def test_refuse_toml_symlink_outside_the_project(self):
        outside = self.root / "secret.toml"
        outside.write_text('name = "dehors"\n', encoding="utf-8")
        trick = self.root / "trick"
        trick.mkdir()
        (trick / "dashboard.toml").symlink_to(outside)
        with self.assertRaises(RegistryError) as exc:
            self.reg.open_path(str(trick), self.root)
        self.assertEqual(str(exc.exception), "dashboard.toml hors du projet")

    def test_open_does_not_write_inside_the_project(self):
        before = sorted(p.name for p in self.alpha.iterdir())
        self.reg.open_path(str(self.alpha), self.root)
        after = sorted(p.name for p in self.alpha.iterdir())
        self.assertEqual(before, after)

    def test_close_removes_the_tab_and_keeps_the_files(self):
        self.reg.open_path(str(self.alpha), self.root)
        self.reg.open_path(str(self.beta), self.root)
        snap = self.reg.close("alpha")
        self.assertEqual([p["id"] for p in snap["projects"]], ["beta"])
        self.assertEqual(snap["active"], "beta")
        self.assertTrue((self.alpha / "DECISIONS.md").is_file())
        with self.assertRaises(RegistryError):
            self.reg.close("alpha")

    def test_missing_folder_stays_listed_with_an_error(self):
        self.reg.open_path(str(self.alpha), self.root)
        for child in self.alpha.iterdir():
            child.unlink()
        self.alpha.rmdir()
        card = self.reg.snapshot()["projects"][0]
        self.assertEqual(card["error"], "projet introuvable")
        self.assertNotIn(str(self.alpha), json.dumps(card))

    def test_registry_file_is_private(self):
        self.reg.open_path(str(self.alpha), self.root)
        mode = (self.root / "reg.json").stat().st_mode & 0o777
        self.assertEqual(mode, stat.S_IRUSR | stat.S_IWUSR)
        parent = (self.root / "reg.json").parent
        if parent.name == "dashboard-projet":
            self.assertEqual(parent.stat().st_mode & 0o777, 0o700)

    def test_default_path_follows_xdg_and_not_the_repo(self):
        saved = {
            key: os.environ.get(key)
            for key in ("XDG_CONFIG_HOME", "DASHBOARD_REGISTRY")
        }
        try:
            os.environ.pop("DASHBOARD_REGISTRY", None)
            os.environ["XDG_CONFIG_HOME"] = str(self.root / "cfg")
            path = default_registry_path()
            self.assertEqual(path, self.root / "cfg" / "dashboard-projet" / "projets.json")
            self.assertNotIn("Dashboard_Projet", str(path))
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_corrupt_registry_is_refused(self):
        target = self.root / "reg.json"
        target.write_text("{", encoding="utf-8")
        with self.assertRaises(RegistryError) as exc:
            self.reg.snapshot()
        self.assertEqual(str(exc.exception), "registre illisible")


if __name__ == "__main__":
    unittest.main()
