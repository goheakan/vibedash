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
SCRIPT = REPO / "bin" / "vibedash"


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

    def test_default_command_serves_the_current_project(self):
        folder = self.root / "vide"
        folder.mkdir()
        init = self.run_script(["init"], folder)
        self.assertEqual(init.returncode, 0, init.stderr)
        proc = subprocess.Popen(
            [str(SCRIPT), "--port", "0", "--registry", str(self.root / "defaut.json")],
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
        finally:
            proc.terminate()
            proc.wait(timeout=3)
            if proc.stdout is not None:
                proc.stdout.close()

    def test_dump_uses_the_current_project_without_a_home_path(self):
        folder = self.root / "vide"
        folder.mkdir()
        init = self.run_script(["init"], folder)
        self.assertEqual(init.returncode, 0, init.stderr)
        proc = self.run_script(["--dump"], folder)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Nom du projet", proc.stdout)
        self.assertNotIn("/home/", proc.stdout)
        self.assertNotIn(str(folder), proc.stdout)

    def test_serve_without_toml_fails_without_echoing_the_path(self):
        folder = self.root / "vide"
        folder.mkdir()
        proc = self.run_script(["serve", "--port", "0"], folder)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("dashboard.toml", proc.stderr)
        self.assertNotIn(str(folder), proc.stderr)
        self.assertNotIn("/home/", proc.stderr)

    def test_init_without_vendor_skips_the_engine_copy(self):
        folder = self.root / "vide"
        folder.mkdir()
        created = init_project(folder)
        self.assertEqual(created, ["dashboard.toml", "DECISIONS.md"])
        self.assertFalse((folder / "dashboard-moteur").exists())
        self.assertFalse((folder / "scripts").exists())

    def test_vendor_copies_the_engine_without_tests_or_cache(self):
        folder = self.root / "vide"
        folder.mkdir()
        created = init_project(folder, vendor=True)
        self.assertEqual(
            created,
            ["dashboard.toml", "DECISIONS.md", "dashboard-moteur/", "scripts/dashboard.sh"],
        )
        motor = folder / "dashboard-moteur"
        self.assertTrue((motor / "server.py").is_file())
        self.assertTrue((motor / "static" / "index.html").is_file())
        self.assertFalse((motor / "tests").exists())
        self.assertFalse(list(motor.rglob("__pycache__")))
        self.assertFalse(list(motor.rglob("*.pyc")))
        script = folder / "scripts" / "dashboard.sh"
        text = script.read_text(encoding="utf-8")
        self.assertIn("dashboard-moteur", text)
        self.assertNotIn("/home/", text)
        self.assertNotIn("Grok_Build", text)
        self.assertTrue(script.stat().st_mode & 0o111)

    def test_vendor_leaves_an_existing_engine_and_script(self):
        folder = self.root / "deja"
        folder.mkdir()
        motor = folder / "dashboard-moteur"
        motor.mkdir()
        (motor / "server.py").write_text("GARDE\n", encoding="utf-8")
        scripts = folder / "scripts"
        scripts.mkdir()
        (scripts / "dashboard.sh").write_text("GARDE\n", encoding="utf-8")
        created = init_project(folder, vendor=True)
        self.assertNotIn("dashboard-moteur/", created)
        self.assertNotIn("scripts/dashboard.sh", created)
        self.assertEqual((motor / "server.py").read_text(encoding="utf-8"), "GARDE\n")
        self.assertEqual((scripts / "dashboard.sh").read_text(encoding="utf-8"), "GARDE\n")

    def test_vendor_does_not_follow_an_engine_symlink(self):
        folder = self.root / "lien"
        folder.mkdir()
        outside = self.root / "dehors"
        outside.mkdir()
        (folder / "dashboard-moteur").symlink_to(outside, target_is_directory=True)
        created = init_project(folder, vendor=True)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertNotIn("dashboard-moteur/", created)

    def test_vendor_does_not_write_through_a_scripts_symlink(self):
        folder = self.root / "lien"
        folder.mkdir()
        outside = self.root / "dehors"
        outside.mkdir()
        (folder / "scripts").symlink_to(outside, target_is_directory=True)
        created = init_project(folder, vendor=True)
        self.assertFalse((outside / "dashboard.sh").exists())
        self.assertNotIn("scripts/dashboard.sh", created)
        self.assertTrue((folder / "dashboard-moteur" / "server.py").is_file())

    def test_init_rejects_an_unknown_argument(self):
        folder = self.root / "vide"
        folder.mkdir()
        proc = self.run_script(["init", "--vendor", "autre"], folder)
        self.assertEqual(proc.returncode, 1)
        self.assertFalse((folder / "dashboard.toml").exists())
        self.assertFalse((folder / "dashboard-moteur").exists())

    def test_vendor_second_run_changes_nothing(self):
        folder = self.root / "vide"
        folder.mkdir()
        first = self.run_script(["init", "--vendor"], folder)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("Créé :", first.stdout)
        before = _snapshot(folder)
        second = self.run_script(["init", "--vendor"], folder)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("Déjà en place", second.stdout)
        self.assertEqual(_snapshot(folder), before)

    def test_copied_kit_serves_without_this_repository(self):
        folder = self.root / "kit"
        folder.mkdir()
        init = self.run_script(["init", "--vendor"], folder)
        self.assertEqual(init.returncode, 0, init.stderr)
        copied = self.root / "ailleurs"
        copy = subprocess.run(["cp", "-a", str(folder), str(copied)], check=False)
        self.assertEqual(copy.returncode, 0)
        script = copied / "scripts" / "dashboard.sh"
        text = script.read_text(encoding="utf-8")
        self.assertNotIn("/home/", text)
        self.assertNotIn("Grok_Build", text)
        self.assertNotIn(str(REPO), text)
        proc = subprocess.Popen(
            [str(script), "--port", "0", "--registry", str(self.root / "kit.json")],
            cwd=copied,
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
            command = Path(f"/proc/{proc.pid}/cmdline").read_bytes().replace(b"\0", b" ").decode()
            engine = str((copied / "dashboard-moteur" / "server.py").resolve())
            self.assertIn(engine, command)
            self.assertNotIn(str((REPO / "moteur" / "server.py").resolve()), command)
            with urllib.request.urlopen(url + "/api/state", timeout=2) as res:
                body = json.loads(res.read().decode())
            self.assertEqual(body["project"]["name"], "Nom du projet")
            self.assertNotIn("/home/", json.dumps(body))
            with urllib.request.urlopen(url + "/", timeout=2) as res:
                page = res.read().decode()
            self.assertIn("VibeDash", page)
            self.assertNotIn("/home/", page)
        finally:
            proc.terminate()
            proc.wait(timeout=3)
            if proc.stdout is not None:
                proc.stdout.close()
            if proc.stderr is not None:
                proc.stderr.close()

    def test_vendored_script_ignores_an_engine_symlink_that_leaves_the_folder(self):
        folder = self.root / "kit"
        folder.mkdir()
        created = init_project(folder, vendor=True)
        self.assertIn("scripts/dashboard.sh", created)
        outside = self.root / "dehors.py"
        outside.write_text("print('DEHORS')\n", encoding="utf-8")
        engine = folder / "dashboard-moteur" / "server.py"
        engine.unlink()
        engine.symlink_to(outside)
        proc = subprocess.run(
            [str(folder / "scripts" / "dashboard.sh"), "--dump"],
            cwd=folder,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotIn("DEHORS", proc.stdout)
        self.assertNotIn("DEHORS", proc.stderr)
        self.assertNotEqual(proc.returncode, 0)


def _snapshot(folder: Path) -> list[tuple[str, bytes]]:
    rows = []
    for path in sorted(folder.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_file() and not path.is_symlink():
            rows.append((str(path.relative_to(folder)), path.read_bytes()))
    return rows


if __name__ == "__main__":
    unittest.main()
