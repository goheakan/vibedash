#!/usr/bin/env python3
"""VibeDash. Tableau local. Un processus, un port, plusieurs projets.

Écoute 127.0.0.1 uniquement. Le port d'un dashboard.toml n'est pas écouté :
le tableau utilise --port, sinon 3847.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from parse import ParseError, load
from registry import Registry, RegistryError, default_registry_path, public_message
from scaffold import InitError, init_project

ENGINE = Path(__file__).resolve().parent
STATIC = ENGINE / "static"
HOST_FORCED = "127.0.0.1"
DEFAULT_PORT = 3847
MAX_BODY = 4096


def _status_for(exc: RegistryError) -> tuple[int, str]:
    msg = public_message(str(exc))
    if msg == "registre illisible":
        return 500, msg
    return 400, msg


def read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = handler.headers.get("Content-Length")
    if length is None:
        raise RegistryError("corps manquant")
    try:
        size = int(length)
    except ValueError as exc:
        raise RegistryError("corps refusé") from exc
    if size < 0 or size > MAX_BODY:
        raise RegistryError("corps refusé")
    raw = handler.rfile.read(size)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryError("json refusé") from exc
    if not isinstance(data, dict):
        raise RegistryError("json refusé")
    return data


def build_handler(registry: Registry):
    class Handler(BaseHTTPRequestHandler):
        server_version = "projet-dashboard/1"

        def log_message(self, format, *args):
            sys.stderr.write(f"{self.address_string()} - {format % args}\n")

        def _send(self, code: int, body: bytes, mime: str):
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data:; connect-src 'self'; "
                "style-src 'self'; script-src 'self'; base-uri 'none'; "
                "form-action 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, payload: dict):
            body = json.dumps(payload, ensure_ascii=False).encode()
            self._send(code, body, "application/json; charset=utf-8")

        def _fail(self, exc: RegistryError):
            code, msg = _status_for(exc)
            self._json(code, {"error": msg})

        def do_GET(self):
            try:
                self._get()
            except RegistryError as exc:
                self._fail(exc)

        def do_POST(self):
            try:
                self._post()
            except RegistryError as exc:
                self._fail(exc)

        def do_DELETE(self):
            try:
                self._delete()
            except RegistryError as exc:
                self._fail(exc)

        def _get(self):
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            if path in {"/", "/index.html"}:
                data = (STATIC / "index.html").read_bytes()
                self._send(200, data, "text/html; charset=utf-8")
                return
            if path == "/api/projects":
                self._json(200, registry.snapshot())
                return
            if path == "/api/state":
                self._state(parse_qs(parsed.query).get("project", [""])[0])
                return
            if path.startswith("/static/"):
                self._static(path[len("/static/"):])
                return
            self._send(404, b"not found", "text/plain; charset=utf-8")

        def _state(self, pid: str):
            if not pid:
                snap = registry.snapshot()
                pid = snap["active"]
            if not pid:
                self._json(200, {"empty": True, "workspace": registry.snapshot()})
                return
            try:
                root = registry.path_of(pid)
            except RegistryError:
                self._json(404, {"error": "projet inconnu"})
                return
            try:
                payload = load(root)
            except ParseError as exc:
                self._json(500, {"error": public_message(str(exc))})
                return
            payload["project"]["id"] = pid
            payload["workspace"] = registry.snapshot()
            payload["empty"] = False
            self._json(200, payload)

        def _static(self, rel: str):
            if not rel or ".." in rel.split("/") or rel.startswith("/"):
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            target = (STATIC / rel).resolve()
            if STATIC.resolve() not in target.parents and target != STATIC.resolve():
                self._send(403, b"forbidden", "text/plain; charset=utf-8")
                return
            if not target.is_file():
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if target.suffix == ".js":
                mime = "text/javascript; charset=utf-8"
            elif target.suffix == ".css":
                mime = "text/css; charset=utf-8"
            elif target.suffix == ".svg":
                mime = "image/svg+xml"
            self._send(200, target.read_bytes(), mime)

        def _post(self):
            path = unquote(urlparse(self.path).path)
            data = read_json(self)
            if path == "/api/projects":
                raw = data.get("path")
                card = registry.open_path(raw, Path.cwd())
                self._json(200, {"project": card, "workspace": registry.snapshot()})
                return
            if path == "/api/active":
                pid = data.get("id")
                if not isinstance(pid, str):
                    raise RegistryError("projet inconnu")
                self._json(200, {"workspace": registry.activate(pid)})
                return
            self._send(404, b"not found", "text/plain; charset=utf-8")

        def _delete(self):
            path = unquote(urlparse(self.path).path)
            prefix = "/api/projects/"
            if not path.startswith(prefix) or path.find("/", len(prefix)) != -1:
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            self._json(200, {"workspace": registry.close(path[len(prefix):])})

    return Handler


def cmd_init(argv: list[str]) -> int:
    if argv:
        print("erreur : init agit sur le dossier courant, sans autre argument", file=sys.stderr)
        return 1
    try:
        created = init_project(Path.cwd())
    except InitError as exc:
        print(f"erreur : {public_message(str(exc))}", file=sys.stderr)
        return 1
    if created:
        print("Créé : " + ", ".join(created), flush=True)
    else:
        print("Déjà en place.", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    args_in = list(sys.argv[1:] if argv is None else argv)
    if args_in[:1] == ["init"]:
        return cmd_init(args_in[1:])
    project_default = ""
    if args_in[:1] == ["serve"]:
        project_default = "."
        args_in = args_in[1:]

    parser = argparse.ArgumentParser(description="VibeDash, tableau local (127.0.0.1), plusieurs projets.")
    parser.add_argument("--project", default="", help="Ouvre ce dossier dans le tableau (optionnel)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port du tableau (défaut 3847)")
    parser.add_argument("--registry", default="", help="Fichier du registre (sinon XDG ou DASHBOARD_REGISTRY)")
    parser.add_argument("--dump", action="store_true", help="Afficher l'état JSON d'un projet et quitter")
    args = parser.parse_args(args_in)
    project = args.project or project_default

    if args.dump:
        if not project:
            print("erreur : --dump exige --project", file=sys.stderr)
            return 1
        try:
            state = load(Path(project).resolve())
        except ParseError as exc:
            print(f"erreur : {public_message(str(exc))}", file=sys.stderr)
            return 1
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0

    if args.registry:
        reg_path = Path(args.registry).expanduser()
        if not reg_path.is_absolute():
            reg_path = Path.cwd() / reg_path
    else:
        reg_path = default_registry_path()
    registry = Registry(reg_path)
    if project:
        try:
            card = registry.open_path(project, Path.cwd())
        except RegistryError as exc:
            print(f"erreur : {public_message(str(exc))}", file=sys.stderr)
            return 1
        print(f"Ouvert : {card['name']}", flush=True)

    host = HOST_FORCED
    try:
        httpd = ThreadingHTTPServer((host, args.port), build_handler(registry))
    except OSError:
        print(f"erreur : le port {args.port} est déjà pris sur {host}", file=sys.stderr)
        return 1
    bound = httpd.server_address[1]
    print(f"VibeDash — http://{host}:{bound}", flush=True)
    print("Un onglet par projet. Ctrl+C pour arrêter.", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\narrêt")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
