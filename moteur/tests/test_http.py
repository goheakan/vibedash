#!/usr/bin/env python3
"""Un seul serveur sert plusieurs projets. Les chemins ne sortent pas en JSON."""

import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from registry import Registry
from server import HOST_FORCED, ThreadingHTTPServer, build_handler, main
from test_registry import write_project


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.reg_path = self.root / "reg.json"
        self.alpha = self.root / "alpha"
        self.beta = self.root / "beta"
        write_project(self.alpha, "Alpha", "D1")
        write_project(self.beta, "Beta", "D9")
        self.registry = Registry(self.reg_path)
        self.httpd = ThreadingHTTPServer((HOST_FORCED, 0), build_handler(self.registry))
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]
        self.assertEqual(self.httpd.server_address[0], HOST_FORCED)
        urllib.request.urlopen(f"http://{HOST_FORCED}:{self.port}/api/projects", timeout=2).close()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)
        self.tmp.cleanup()

    def request(self, method, path, payload=None):
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            f"http://{HOST_FORCED}:{self.port}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                body = res.read().decode()
                return res.status, body, res.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode()
                return exc.code, body, exc.headers.get("Content-Type", "")
            finally:
                exc.close()

    def test_empty_workspace_then_two_tabs_on_one_port(self):
        status, body, mime = self.request("GET", "/api/projects")
        self.assertEqual(status, 200)
        self.assertIn("application/json", mime)
        self.assertEqual(json.loads(body)["projects"], [])
        status, body, _mime = self.request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["empty"])

        status, body, _mime = self.request("POST", "/api/projects", {"path": str(self.alpha)})
        self.assertEqual(status, 200)
        opened = json.loads(body)
        self.assertEqual(opened["project"]["name"], "Alpha")
        self.assertNotIn(str(self.alpha), body)

        status, body, _mime = self.request("POST", "/api/projects", {"path": str(self.beta)})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["workspace"]["active"], "beta")

        status, body, _mime = self.request("GET", "/api/state?project=alpha")
        self.assertEqual(status, 200)
        alpha = json.loads(body)
        self.assertEqual(alpha["project"]["id"], "alpha")
        self.assertEqual([d["id"] for d in alpha["decisions"]], ["D1"])
        self.assertNotIn("D9", body)
        self.assertNotIn(str(self.root), body)
        self.assertNotIn("/home/", body)

        status, body, _mime = self.request("GET", "/api/state?project=beta")
        beta = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual([d["id"] for d in beta["decisions"]], ["D9"])
        self.assertNotIn("choix Alpha", body)

        page, html, mime = self.request("GET", "/")
        self.assertEqual(page, 200)
        self.assertIn("text/html", mime)
        self.assertIn('id="tabs"', html)
        self.assertIn('id="open-project"', html)

    def test_model_state_contains_its_decisions_and_the_page_keeps_the_csp(self):
        model = Path(__file__).resolve().parents[2] / "modele"
        status, body, _mime = self.request("POST", "/api/projects", {"path": str(model)})
        self.assertEqual(status, 200, body)
        opened = json.loads(body)
        self.assertNotIn(str(model), body)
        project_id = opened["project"]["id"]
        status, body, _mime = self.request("GET", "/api/state?project=" + project_id)
        self.assertEqual(status, 200, body)
        state = json.loads(body)
        self.assertEqual([item["id"] for item in state["decisions"]], ["D1"])
        self.assertEqual(state["decisions"][0]["title"], "Première décision")
        self.assertEqual(state["decisions"][0]["bucket"], "pending")
        self.assertIn("Pas encore tranché", body)
        self.assertNotIn("/home/", body)
        self.assertNotIn(str(model), body)
        status, html, mime = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", mime)
        csp = (
            "default-src 'self'; img-src 'self' data:; connect-src 'self'; "
            "style-src 'self'; script-src 'self'; base-uri 'none'; "
            "form-action 'none'; frame-ancestors 'none'"
        )
        self.assertIn(csp, html)
        self.assertNotIn("unsafe-inline", html)
        self.assertNotIn("unsafe-eval", html)
        status, script, mime = self.request("GET", "/static/app.js")
        self.assertEqual(status, 200)
        self.assertIn("javascript", mime)
        self.assertIn("Ctrl+K", script)
        self.assertIn("dans la recherche", script)

    def test_refuse_a_folder_without_toml_without_echoing_the_path(self):
        secret = str(self.root / "absent")
        status, body, _mime = self.request("POST", "/api/projects", {"path": secret})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "dossier introuvable")
        self.assertNotIn(secret, body)
        status, body, _mime = self.request("POST", "/api/projects", {"path": "/etc/passwd"})
        self.assertEqual(status, 400)
        self.assertNotIn("/etc/passwd", body)

    def test_close_keeps_files_and_unknown_id_fails(self):
        self.request("POST", "/api/projects", {"path": str(self.alpha)})
        self.request("POST", "/api/projects", {"path": str(self.beta)})
        status, body, _mime = self.request("DELETE", "/api/projects/alpha")
        self.assertEqual(status, 200)
        self.assertEqual([p["id"] for p in json.loads(body)["workspace"]["projects"]], ["beta"])
        self.assertTrue((self.alpha / "dashboard.toml").is_file())
        status, body, _mime = self.request("DELETE", "/api/projects/alpha")
        self.assertEqual(status, 400)
        status, body, _mime = self.request("DELETE", "/api/projects/..")
        self.assertEqual(status, 400)

    def test_activate_remembers_the_tab(self):
        self.request("POST", "/api/projects", {"path": str(self.alpha)})
        self.request("POST", "/api/projects", {"path": str(self.beta)})
        status, body, _mime = self.request("POST", "/api/active", {"id": "alpha"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["workspace"]["active"], "alpha")
        status, body, _mime = self.request("GET", "/api/projects")
        self.assertEqual(json.loads(body)["active"], "alpha")
        self.assertNotIn(str(self.alpha), body)

    def test_dump_prints_one_project_and_does_not_create_a_registry(self):
        saved = os.environ.get("DASHBOARD_REGISTRY")
        os.environ["DASHBOARD_REGISTRY"] = str(self.reg_path)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                code = main(["--dump", "--project", str(self.alpha)])
        finally:
            if saved is None:
                os.environ.pop("DASHBOARD_REGISTRY", None)
            else:
                os.environ["DASHBOARD_REGISTRY"] = saved
        self.assertEqual(code, 0)
        text = buf.getvalue()
        self.assertIn("Alpha", text)
        self.assertNotIn(str(self.alpha), text)
        self.assertFalse(self.reg_path.exists())

    def test_client_asks_the_project_api(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("/api/projects", js)
        self.assertIn('data-act="open"', js)
        self.assertIn("data-project", js)


class GuideTests(unittest.TestCase):
    def test_guides_document_the_keyboard(self):
        repo = Path(__file__).resolve().parents[2]
        guides = {
            "README.md": "## Clavier",
            "README.en.md": "## Keyboard",
            "README.es.md": "## Teclado",
        }
        for name, heading in guides.items():
            text = (repo / name).read_text(encoding="utf-8")
            self.assertIn(heading, text)
            self.assertIn("`o`", text)
            self.assertIn("`/`", text)
            self.assertIn("Ctrl+K", text)
            self.assertIn("`j` / `k`", text)
            self.assertIn("`?`", text)
        french = (repo / "README.md").read_text(encoding="utf-8")
        english = (repo / "README.en.md").read_text(encoding="utf-8")
        spanish = (repo / "README.es.md").read_text(encoding="utf-8")
        self.assertIn("Dans la recherche", french)
        self.assertIn("In the search", english)
        self.assertIn("En la búsqueda", spanish)


if __name__ == "__main__":
    unittest.main()
