#!/usr/bin/env python3
"""Le script bin/vibedash atteint le moteur sans changer de dossier."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "bin" / "vibedash"
INSTALL = REPO / "install.sh"
FIX = Path(__file__).resolve().parent / "fixtures"


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = os.environ.copy()
        self.env["DASHBOARD_REGISTRY"] = str(self.root / "reg.json")

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, args, cwd=None):
        return subprocess.run(
            [str(SCRIPT), *args],
            cwd=cwd or self.root,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_dump_prints_the_project_and_skips_the_registry(self):
        proc = self.run_script(["--dump", "--project", str(FIX)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Fixture", proc.stdout)
        self.assertNotIn(str(FIX), proc.stdout)
        self.assertFalse((self.root / "reg.json").exists())

    def test_dump_without_a_project_fails(self):
        proc = self.run_script(["--dump"])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("--dump", proc.stderr)
        self.assertFalse((self.root / "reg.json").exists())

    def test_relative_project_uses_the_caller_directory(self):
        proc = self.run_script(["--dump", "--project", "fixtures"], cwd=FIX.parent)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Fixture", proc.stdout)

    def test_local_engine_is_used_when_it_stays_inside_the_folder(self):
        folder = self.root / "kit"
        motor = folder / "dashboard-moteur"
        motor.mkdir(parents=True)
        (motor / "server.py").write_text("print('MOTEUR-LOCAL')\n", encoding="utf-8")
        proc = self.run_script(["--dump"], cwd=folder)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("MOTEUR-LOCAL", proc.stdout)

    def test_engine_symlink_outside_the_folder_is_ignored(self):
        folder = self.root / "kit"
        motor = folder / "dashboard-moteur"
        motor.mkdir(parents=True)
        outside = self.root / "dehors.py"
        outside.write_text("print('DEHORS')\n", encoding="utf-8")
        (motor / "server.py").symlink_to(outside)
        proc = self.run_script(["--dump"], cwd=folder)
        self.assertNotIn("DEHORS", proc.stdout)
        self.assertNotIn("DEHORS", proc.stderr)
        self.assertNotEqual(proc.returncode, 0)

    def test_symlink_still_finds_the_engine(self):
        link = self.root / "dashboard"
        link.symlink_to(SCRIPT)
        proc = subprocess.run(
            [str(link), "--dump", "--project", str(FIX)],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Fixture", proc.stdout)

    def test_install_links_the_command_without_replacing_a_file(self):
        dest = self.root / "commandes"
        env = self.env.copy()
        env["VIBEDASH_BIN_DIR"] = str(dest)
        text = INSTALL.read_text(encoding="utf-8")
        self.assertNotIn("/home/", text)
        self.assertNotIn("sudo", text)
        first = subprocess.run(
            [str(INSTALL)],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("Installé", first.stdout)
        link = dest / "vibedash"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), SCRIPT.resolve())
        again = subprocess.run(
            [str(INSTALL)],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("Déjà en place", again.stdout)
        link.unlink()
        link.write_text("GARDE\n", encoding="utf-8")
        blocked = subprocess.run(
            [str(INSTALL)],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(blocked.returncode, 1)
        self.assertEqual(link.read_text(encoding="utf-8"), "GARDE\n")
        self.assertNotIn(str(dest), blocked.stderr)


if __name__ == "__main__":
    unittest.main()
