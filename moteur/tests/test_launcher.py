#!/usr/bin/env python3
"""Le script bin/dashboard atteint le moteur sans changer de dossier."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "bin" / "dashboard"
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


if __name__ == "__main__":
    unittest.main()
