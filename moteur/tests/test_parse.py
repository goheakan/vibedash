#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parse import ParseError, load, parse_decisions

FIX = Path(__file__).resolve().parent / "fixtures"
MODEL = Path(__file__).resolve().parents[2] / "modele"


class ParseTests(unittest.TestCase):
    def test_table_and_sections(self):
        items = parse_decisions((FIX / "DECISIONS.md").read_text(encoding="utf-8"), "DECISIONS.md")
        self.assertEqual([i["id"] for i in items], ["D1", "D2", "D3"])
        self.assertEqual(items[0]["bucket"], "done")
        self.assertEqual(items[1]["bucket"], "pending")
        self.assertEqual(items[2]["bucket"], "orientation")
        self.assertEqual(items[0]["title"], "Moteur")
        self.assertIn("moteur libre", items[0]["body"])

    def test_load_fixture(self):
        data = load(FIX)
        self.assertEqual(data["project"]["name"], "Fixture")
        self.assertEqual(data["stats"]["pending"], 2)
        self.assertEqual(data["milestones"][0]["bucket"], "done")
        self.assertEqual(data["milestones"][1]["bucket"], "current")
        self.assertTrue(all("/home/" not in str(v) for v in data["docs"]))
        play = next(x for x in data["sales"] if x["id"] == "PLAY")
        self.assertEqual(play["bucket"], "pending")
        self.assertEqual(data["sales"][0]["id"], "D3")

    def test_model_lists_its_pending_decision(self):
        data = load(MODEL)
        decisions = data["decisions"]
        self.assertEqual([item["id"] for item in decisions], ["D1"])
        self.assertEqual(decisions[0]["title"], "Première décision")
        self.assertEqual(decisions[0]["bucket"], "pending")
        self.assertIn("Pas encore tranché", decisions[0]["body"])
        self.assertNotIn("/home/", decisions[0]["body"])

    def test_refuse_secret(self):
        from parse import resolve_allowed
        with self.assertRaises(ParseError):
            resolve_allowed(FIX, ".env")


if __name__ == "__main__":
    unittest.main()
