#!/usr/bin/env python3
"""init crée le socle sans l'écraser. serve montre le nom sur 127.0.0.1."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scaffold import init_project

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "bin" / "dashboard"


class InitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = os.environ.copy()
        self.env["DASHBOARD_REGISTRY"] = str(self.root / "reg.json")
        self.env["PYTHONUNBUFFERED"] = "1"

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, args, cwd):
        return subprocess.run(
            [str(SCRIPT), *args],
            cwd=cwd,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_init_writes_the_two_files_with_relative_paths(self):
        folder = self.root / "vide"
        folder.mkdir()
        created = init_project(folder)
        self.assertEqual(created, ["dashboard.toml", "DECISIONS.md"])
        toml = (folder / "dashboard.toml").read_text(encoding="utf-8")
        decisions = (folder / "DECISIONS.md").read_text(encoding="utf-8")
        self.assertIn('name = "Nom du projet"', toml)
        self.assertIn('decisions = "DECISIONS.md"', toml)
        self.assertIn('jalon_glob = "J*.md"', toml)
        self.assertNotIn("/home/", toml)
        self.assertNotIn("/home/", decisions)
        self.assertIn("D1", decisions)

    def test_init_leaves_an_existing_file_untouched(self):
        folder = self.root / "deja"
        folder.mkdir()
        kept = folder / "dashboard.toml"
        kept.write_text('name = "Gardé"\n', encoding="utf-8")
        note = folder / "DECISIONS.md"
        note.write_text("NE PAS ECRASER\n", encoding="utf-8")
        created = init_project(folder)
        self.assertEqual(created, [])
        self.assertEqual(kept.read_text(encoding="utf-8"), 'name = "Gardé"\n')
        self.assertEqual(note.read_text(encoding="utf-8"), "NE PAS ECRASER\n")

    def test_init_fills_only_the_missing_file(self):
        folder = self.root / "moitie"
        folder.mkdir()
        (folder / "DECISIONS.md").write_text("DEJA\n", encoding="utf-8")
        created = init_project(folder)
        self.assertEqual(created, ["dashboard.toml"])
        self.assertEqual((folder / "DECISIONS.md").read_text(encoding="utf-8"), "DEJA\n")

    def test_command_init_then_serve_shows_the_project_name(self):
        folder = self.root / "vide"
        folder.mkdir()
        init = self.run_script(["init"], folder)
        self.assertEqual(init.returncode, 0, init.stderr)
        self.assertIn("dashboard.toml", init.stdout)
        again = self.run_script(["init"], folder)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("Déjà en place", again.stdout)
        self.assertIn('name = "Nom du projet"', (folder / "dashboard.toml").read_text(encoding="utf-8"))

        proc = subprocess.Popen(
            [str(SCRIPT), "serve", "--port", "0", "--registry", str(self.root / "serve.json")],
            cwd=folder,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        url = ""
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                if "http://127.0.0.1:" in line:
                    url = line.strip().split()[-1]
                    break
            self.assertTrue(url.startswith("http://127.0.0.1:"), url)
            with urllib.request.urlopen(url + "/api/state", timeout=2) as res:
                body = json.loads(res.read().decode())
            self.assertEqual(body["project"]["name"], "Nom du projet")
            self.assertNotIn("/home/", json.dumps(body))
            with urllib.request.urlopen(url + "/", timeout=2) as res:
                page = res.read().decode()
            self.assertIn("VibeDash", page)
        finally:
            proc.terminate()
            proc.wait(timeout=3)
            if proc.stdout is not None:
                proc.stdout.close()

    def test_serve_without_toml_fails_without_echoing_the_path(self):
        folder = self.root / "vide"
        folder.mkdir()
        proc = self.run_script(["serve", "--port", "0"], folder)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("dashboard.toml", proc.stderr)
        self.assertNotIn(str(folder), proc.stderr)
        self.assertNotIn("/home/", proc.stderr)


if __name__ == "__main__":
    unittest.main()
