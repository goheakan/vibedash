#!/usr/bin/env python3
"""Lit dashboard.toml + Markdown. Aucun chemin personnel dans la sortie."""

from __future__ import annotations

import glob
import re
import tomllib
from datetime import UTC, datetime
from pathlib import Path

TABLE_SEP = re.compile(r"^\|[\s:|-]+\|\s*$")
ROW = re.compile(
    r"^\|\s*(?P<id>D\d+)\s*\|\s*(?P<status>.*?)\s*\|\s*(?P<date>.*?)\s*\|\s*(?P<choice>.*?)\s*\|\s*$"
)
H_DECISION = re.compile(r"^##\s+(?P<id>D\d+)\s+[—–-]\s+(?P<title>.+?)\s*$")
H_JALON = re.compile(r"^#{2,3}\s+(?P<id>J\d+)\s+[—–-]\s+(?P<title>.+?)\s*$")
BOLD = re.compile(r"\*\*(.*?)\*\*")

FORBIDDEN_NAMES = (
    ".env",
    "auth.json",
    "wp-config.php",
    "id_rsa",
    "id_ed25519",
)


class ParseError(ValueError):
    pass


def strip_md(text: str) -> str:
    text = BOLD.sub(r"\1", text or "")
    return re.sub(r"\s+", " ", text).strip()


def bucket_status(raw: str) -> str:
    s = (raw or "").lower()
    if "tranché" in s or "tranche" in s or s in {"fait", "done", "ok"}:
        return "done"
    if "orientation" in s:
        return "orientation"
    if s in {"en cours", "current"}:
        return "current"
    return "pending"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        # Fichier autorisé hors racine (ex. PLAN dans le dossier parent).
        return path.name


def resolve_allowed(root: Path, rel: str) -> Path:
    if not rel or rel.startswith("/"):
        raise ParseError(f"chemin refusé : {rel!r}")
    name = Path(rel).name.lower()
    if name in FORBIDDEN_NAMES or name.endswith(".env"):
        raise ParseError(f"fichier sensible refusé : {rel}")
    target = (root / rel).resolve()
    root_res = root.resolve()
    # Autoriser la racine et un niveau parent (plan du dossier voisin).
    if target == root_res:
        raise ParseError("la racine n'est pas un fichier")
    if root_res not in target.parents and root_res.parent not in target.parents:
        raise ParseError(f"hors périmètre : {rel}")
    if not target.is_file():
        raise ParseError(f"introuvable : {rel}")
    return target


def parse_decisions(text: str, file_rel: str) -> list[dict]:
    sections: dict[str, dict] = {}
    current = None
    body: list[str] = []
    for line in text.splitlines():
        m = H_DECISION.match(line)
        if m:
            if current:
                sections[current]["body"] = "\n".join(body).strip()
            current = m.group("id")
            sections[current] = {"title": strip_md(m.group("title")), "body": ""}
            body = []
        elif current:
            body.append(line)
    if current:
        sections[current]["body"] = "\n".join(body).strip()

    items: list[dict] = []
    seen: set[str] = set()
    for line in text.splitlines():
        if TABLE_SEP.match(line):
            continue
        m = ROW.match(line)
        if not m:
            continue
        did = m.group("id")
        if did in seen:
            continue
        seen.add(did)
        raw = strip_md(m.group("status"))
        summary = strip_md(m.group("choice"))
        sec = sections.get(did, {})
        items.append(
            {
                "id": did,
                "title": sec.get("title") or summary or did,
                "status": raw,
                "bucket": bucket_status(raw),
                "date": strip_md(m.group("date")),
                "summary": summary,
                "body": sec.get("body") or "",
                "file": file_rel,
                "lane": "decisions",
            }
        )
    return items


def parse_plan_jalons(text: str) -> list[dict]:
    found: list[dict] = []
    seen: set[str] = set()
    for line in text.splitlines():
        m = H_JALON.match(line)
        if not m:
            continue
        jid = m.group("id")
        if jid in seen:
            continue
        seen.add(jid)
        found.append({"id": jid, "title": strip_md(m.group("title"))})
    found.sort(key=lambda x: int(re.sub(r"\D", "", x["id"]) or 0))
    return found


def first_blurb(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        if s.startswith("#") or low.startswith("date") or low in {"fait", "preuves", "suite"}:
            continue
        if s.startswith("- "):
            s = s[2:].strip()
        blurb = strip_md(s)
        if len(blurb) > 110:
            blurb = blurb[:107].rsplit(" ", 1)[0] + "…"
        return blurb
    return ""


def jalon_files(root: Path, pattern: str) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for match in sorted(glob.glob(str(root / pattern))):
        p = Path(match)
        if not p.is_file():
            continue
        m = re.match(r"(J\d+)", p.stem)
        if m:
            out[m.group(1)] = p
    return out


def load(root: Path) -> dict:
    root = Path(root).resolve()
    cfg_path = root / "dashboard.toml"
    if not cfg_path.is_file():
        raise ParseError("dashboard.toml introuvable dans ce projet")
    with cfg_path.open("rb") as fh:
        cfg = tomllib.load(fh)

    name = str(cfg.get("name") or root.name)
    sources = cfg.get("sources") or {}
    decisions_rel = sources.get("decisions") or "DECISIONS.md"
    decisions_path = resolve_allowed(root, decisions_rel)
    decisions = parse_decisions(_read(decisions_path), _rel(decisions_path, root))

    catalog: list[dict] = []
    for row in cfg.get("milestones") or []:
        if not row.get("id"):
            continue
        catalog.append({"id": str(row["id"]), "title": str(row.get("title") or row["id"])})
    plan_rel = sources.get("plan")
    if not catalog and plan_rel:
        try:
            plan_path = resolve_allowed(root, plan_rel)
            catalog = parse_plan_jalons(_read(plan_path))
        except ParseError:
            catalog = []

    logs = jalon_files(root, sources.get("jalon_glob") or "J*.md")
    current_set = False
    milestones: list[dict] = []
    for row in catalog:
        jid = row["id"]
        log = logs.get(jid)
        if log:
            bucket = "done"
            blurb = first_blurb(_read(log))
            file_rel = _rel(log, root)
        elif not current_set:
            bucket = "current"
            current_set = True
            blurb = "Pas encore commencé."
            file_rel = ""
        else:
            bucket = "upcoming"
            blurb = ""
            file_rel = ""
        milestones.append(
            {
                "id": jid,
                "title": row["title"],
                "status": {"done": "fait", "current": "en cours", "upcoming": "à venir"}[bucket],
                "bucket": bucket,
                "summary": blurb,
                "body": _read(log) if log else "",
                "file": file_rel,
                "lane": "dev",
                "date": "",
            }
        )

    sales_cfg = (cfg.get("lanes") or {}).get("sales") or {}
    sales_ids = [str(x) for x in sales_cfg.get("decision_ids") or []]
    by_id = {d["id"]: d for d in decisions}
    sales: list[dict] = []
    for did in sales_ids:
        if did in by_id:
            item = dict(by_id[did])
            item["lane"] = "sales"
            sales.append(item)

    extras = []
    for extra in cfg.get("extras") or []:
        eid = str(extra.get("id") or "")
        if not eid:
            continue
        from_j = extra.get("from_jalon")
        bucket = bucket_status(str(extra.get("status") or "pending"))
        body = str(extra.get("body") or "")
        file_rel = ""
        if from_j:
            match = next((m for m in milestones if m["id"] == from_j), None)
            if match:
                bucket = match["bucket"] if match["bucket"] != "upcoming" else "pending"
                if match["bucket"] == "current":
                    bucket = "pending"
                body = match.get("body") or body
                file_rel = match.get("file") or ""
        extras.append(
            {
                "id": eid,
                "title": str(extra.get("title") or eid),
                "status": str(extra.get("status") or {"done": "fait", "pending": "en attente", "orientation": "orientation"}.get(bucket, "en attente")),
                "bucket": bucket,
                "date": "",
                "summary": str(extra.get("summary") or ""),
                "body": body,
                "file": file_rel,
                "lane": str(extra.get("lane") or "sales"),
            }
        )
        if extras[-1]["lane"] == "sales":
            sales.append(extras[-1])

    constraints = [str(c.get("text")) for c in (cfg.get("constraints") or []) if c.get("text")]
    docs = []
    for doc in cfg.get("docs") or []:
        if not doc.get("path"):
            continue
        docs.append({"title": str(doc.get("title") or doc["path"]), "path": str(doc["path"])})

    pending = [d for d in decisions if d["bucket"] in {"pending", "orientation"}]
    current_m = next((m for m in milestones if m["bucket"] == "current"), None)
    now = list(pending)
    if current_m:
        now.append(current_m)

    mtimes = [decisions_path.stat().st_mtime]
    for p in logs.values():
        mtimes.append(p.stat().st_mtime)
    mtimes.append(cfg_path.stat().st_mtime)

    done_d = sum(1 for d in decisions if d["bucket"] == "done")
    done_m = sum(1 for m in milestones if m["bucket"] == "done")

    return {
        "project": {
            "name": name,
            "tagline": str(cfg.get("tagline") or ""),
            "identity": str(cfg.get("identity") or ""),
            "locale": str(cfg.get("locale") or "fr"),
        },
        "bind": {
            "host": str(cfg.get("host") or "127.0.0.1"),
            "port": int(cfg.get("port") or 3847),
        },
        "rev": str(max(mtimes) if mtimes else 0),
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": {
            "decisions_done": done_d,
            "decisions_total": len(decisions),
            "milestones_done": done_m,
            "milestones_total": len(milestones),
            "pending": len(pending),
        },
        "now": now,
        "decisions": decisions,
        "milestones": milestones,
        "sales": sales,
        "constraints": constraints,
        "docs": docs,
        "sales_title": str(sales_cfg.get("title") or "Vente"),
    }


if __name__ == "__main__":
    import json
    import sys

    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    print(json.dumps(load(target), ensure_ascii=False, indent=2))
