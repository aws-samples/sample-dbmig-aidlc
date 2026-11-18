"""Read a migration folder into one data model for the review site (read-only)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import gates
from ..project import APP_DIR, Project, exists, load, load_yaml, propose

_SOURCE_HEAD = re.compile(r"^--- SOURCE[^\n]*? — (\S+)[^\n]*---\s*$", re.M)
_DOC_DIRS = ("00-intake", "01-assessment", "02-construction", "03-validation", "04-operations",
             "05-application")
_SKIP_PARTS = {"prompts", "code_prompts", "test_prompts", "retries", "retries_code", "backup",
               "review", "dms-sc", "_state"}


def _y(path: Path) -> Any:
    try:
        return load_yaml(path) if path.exists() else None
    except Exception:  # noqa: BLE001 - a broken artifact is shown as missing
        return None


def _text(path: Path, limit: int = 400_000) -> Optional[str]:
    try:
        t = path.read_text(errors="replace")
    except OSError:
        return None
    return t if len(t) <= limit else t[:limit] + "\n-- … truncated for the review site …\n"


def slug(*parts: str) -> str:
    s = "-".join(str(p) for p in parts if p)
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_")[:150] or "x"


class _Sources:
    """Source DDL sections of the prompt bundles, by object name."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.cache: Dict[str, Dict[str, str]] = {}

    def get(self, prompt_file: Optional[str], schema: str, name: str) -> Optional[str]:
        if not prompt_file:
            return None
        if prompt_file not in self.cache:
            sections: Dict[str, str] = {}
            text = _text(self.base / prompt_file) or ""
            heads = list(_SOURCE_HEAD.finditer(text))
            for i, m in enumerate(heads):
                end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
                body = text[m.end():end]
                cut = re.search(r"^=== ", body, re.M)
                if cut:
                    body = body[:cut.start()]
                sections[m.group(1).upper()] = body.strip("\n")
            self.cache[prompt_file] = sections
        sec = self.cache[prompt_file]
        return sec.get(f"{schema}.{name}".upper()) or sec.get(name.upper()) or next(
            (v for k, v in sec.items() if k.split(".")[-1] == name.upper()), None)


def _project(ws: Path) -> Project:
    if exists(ws):
        return load(ws, create=False)
    return Project(ws, propose(ws, ws.name))      # in memory only: never write into the folder


def _schemas(proj: Project) -> List[str]:
    out = [s.upper() for s in proj.schemas]
    c = proj.dir / "02-construction"
    for f in sorted(c.glob("*manifest-*.yaml")) if c.is_dir() else []:
        s = f.stem.split("manifest-", 1)[1].upper()
        if s not in out:
            out.append(s)
    return out


def _log_lines(log: str, name: str) -> List[str]:
    if not log:
        return []
    rx = re.compile(rf"(?<![\w$#]){re.escape(name)}(?![\w$#])", re.I)
    return [ln.strip() for ln in log.splitlines() if rx.search(ln)][:20]


def collect(ws: Path) -> Dict[str, Any]:
    ws = Path(ws).resolve()
    proj = _project(ws)
    c, v, a = ws / "02-construction", ws / "03-validation", ws / "01-assessment"
    sources = _Sources(c)
    log = _text(c / "conversion-log.md") or ""
    schemas = _schemas(proj)

    decisions = list(proj.decisions)
    by_obj: Dict[str, List[str]] = {}
    for d in decisions:
        for o in d.get("objects") or []:
            by_obj.setdefault(str(o).upper(), []).append(d["id"])

    objects: List[Dict[str, Any]] = []
    for s in schemas:
        for kind, base in (("table", "manifest"), ("code", "code-manifest")):
            m = _y(c / f"{base}-{s}.yaml") or {}
            for u in m.get("units") or []:
                name = str(u.get("name"))
                otype = str(u.get("object_type") or ("TABLE" if kind == "table" else "CODE"))
                out_rel = u.get("output_file")
                o: Dict[str, Any] = {
                    "id": slug(s, kind, otype, name), "schema": s, "name": name, "kind": kind,
                    "type": otype.upper(), "status": u.get("status") or "pending",
                    "post_status": u.get("post_status"), "attempts": u.get("attempts"),
                    "last_error": u.get("last_error"), "post_last_error": u.get("post_last_error"),
                    "output_file": f"02-construction/{out_rel}" if out_rel else None,
                    "prompt_file": f"02-construction/{u['prompt_file']}" if u.get("prompt_file") else None,
                    "disposition": u.get("disposition"), "origin": u.get("origin"),
                    "action_items": u.get("action_items") or [], "target_name": u.get("target_name"),
                    "rows": u.get("num_rows"),
                }
                o["converted"] = _text(c / out_rel) if out_rel else None
                o["source"] = sources.get(u.get("prompt_file"), s, name)
                if u.get("origin") == "dms_sc" and out_rel:
                    snap = a / "dms-sc" / s / "source" / Path(out_rel).name
                    orig = a / "dms-sc" / s / "target" / Path(out_rel).name
                    o["source"] = o["source"] or _text(snap)
                    o["dms_original"] = _text(orig)
                retries = []
                for key in ("retry_prompt", "post_retry_prompt"):
                    if u.get(key):
                        retries.append({"file": f"02-construction/{u[key]}",
                                        "text": _text(c / u[key], 60_000)})
                o["retries"] = retries
                o["notes"] = [ln.strip() for ln in (o["converted"] or "").splitlines()
                              if ln.strip().startswith("-- dbmig:")]
                o["log"] = _log_lines(log, name)
                o["decisions"] = by_obj.get(f"{s}.{name}".upper(), [])
                objects.append(o)

    # ---- tests -----------------------------------------------------------
    tests: List[Dict[str, Any]] = []
    reconcile: Dict[str, List[Dict[str, Any]]] = {}
    summaries: Dict[str, Dict[str, Any]] = {}
    for s in schemas:
        rep = _y(v / f"equivalence-report-{s}.yaml") or {}
        summaries[s] = dict(rep.get("summary") or {})
        low = {str(x).upper() for x in rep.get("low_coverage") or []}
        results: Dict[tuple, Dict[str, Any]] = {}
        for r in rep.get("results") or []:
            results[(str(r.get("object", "")).upper(), str(r.get("case")))] = r
        tm = _y(v / f"test-manifest-{s}.yaml") or {}
        for u in tm.get("units") or []:
            spec_rel = u.get("spec_file")
            spec = _y(v / spec_rel) if spec_rel else None
            key = f"{s}.{u.get('name')}".upper()
            cases = []
            for case in (spec or {}).get("cases") or []:
                r = results.get((key, str(case.get("id"))), {})
                cases.append({"id": case.get("id"), "description": case.get("description"),
                              "spec": case, "status": r.get("status") or "not run",
                              "detail": r.get("detail"), "coverage": r.get("coverage")})
            for (obj, cid), r in results.items():
                if obj == key and not any(str(x["id"]) == cid for x in cases):
                    cases.append({"id": cid, "description": None, "spec": None,
                                  "status": r.get("status"), "detail": r.get("detail"),
                                  "coverage": r.get("coverage")})
            tests.append({"id": slug("test", s, u.get("name")), "schema": s, "name": u.get("name"),
                          "type": u.get("object_type"), "status": u.get("status"),
                          "spec_file": f"03-validation/{spec_rel}" if spec_rel else None,
                          "notes": (spec or {}).get("notes"), "low_coverage": key in low,
                          "coverage": (u.get("data_coverage") or {}).get("level"), "cases": cases,
                          "object_id": next((o["id"] for o in objects if o["schema"] == s
                                             and o["name"].upper() == str(u.get("name")).upper()), None)})
        rr = _y(v / f"reconcile_report-{s}.yaml") or {}
        if rr.get("results"):
            reconcile[s] = list(rr["results"])
    for o in objects:
        o["tests"] = [t["id"] for t in tests if t.get("object_id") == o["id"]]

    # ---- documents ----------------------------------------------------------
    docs: List[Dict[str, Any]] = []
    for name in ("migration-report.md", "SIGN-OFF.md", "follow-up.md", "README.md"):
        if (ws / name).exists():
            docs.append({"path": name, "phase": "project"})
    for d in _DOC_DIRS:
        base = ws / d
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.md")):
            rel = f.relative_to(ws)
            if any(p in _SKIP_PARTS for p in rel.parts) or f.name.startswith("_context") \
                    or f.name.endswith(".prompt.md"):
                continue
            docs.append({"path": str(rel), "phase": d})
    for doc in docs:
        doc["id"] = slug("doc", doc["path"].replace("/", "_"))
        doc["text"] = _text(ws / doc["path"]) or ""
        m = re.search(r"^#\s+(.+)$", doc["text"], re.M)
        doc["title"] = m.group(1).strip() if m else doc["path"]

    verify: Dict[str, List[Dict[str, Any]]] = {}
    for s in schemas:
        led = (_y(a / f"dms-sc-verification-{s}.yaml") or {}).get("items") or {}
        if led:
            verify[s] = [dict(x, key=k) for k, x in led.items() if isinstance(x, dict)]

    fu = (_y(ws / "follow-up.yaml") or {}).get("items") or []
    app = _app(ws, proj)

    return {
        "dir": str(ws), "project": proj.name, "pair": proj.data.get("pair"),
        "entry": proj.entry_path, "schemas": schemas, "has_project_file": exists(ws),
        "gates": [gates.view(proj, p) for p in proj.gated_phases], "next_gate": gates.next_gate(proj),
        "decisions": decisions, "policies": proj.data.get("policies") or {},
        "intake": proj.data.get("intake") or {},
        "objects": objects, "tests": tests, "reconcile": reconcile, "summaries": summaries,
        "docs": docs, "verify": verify, "followups": [i for i in fu if isinstance(i, dict)],
        "app": app,
    }


def _diff_files(text: str) -> List[Dict[str, Any]]:
    """Split a unified diff (git diff, diff -ru, or diff -u) into per-file chunks."""
    lines = (text or "").splitlines()
    starts_on = "diff " if any(ln.startswith("diff ") for ln in lines) else "--- "
    files: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    for ln in lines:
        if ln.startswith(starts_on):
            cur = {"path": "", "lines": [], "add": 0, "del": 0}
            files.append(cur)
        if cur is None:
            continue
        if ln.startswith("+++ "):
            name = ln[4:].split("\t")[0].strip()
            cur["path"] = name[2:] if name.startswith("b/") else name
        elif ln.startswith("+"):
            cur["add"] += 1
        elif ln.startswith("-") and not ln.startswith("--- "):
            cur["del"] += 1
        cur["lines"].append(ln)
    for f in files:
        if not f["path"]:
            m = re.search(r"\s(\S+)$", f["lines"][0]) if f["lines"] else None
            f["path"] = m.group(1) if m else "?"
    return files


def _app(ws: Path, proj: Project) -> Dict[str, Any]:
    from .. import appmod
    base = ws / APP_DIR
    if not base.is_dir():
        return {"present": False}
    backups = []
    if (base / "backup").is_dir():
        for d in sorted((base / "backup").iterdir()):
            if d.is_dir():
                n = sum(1 for f in d.rglob("*") if f.is_file() and f.name != "MANIFEST.md")
                backups.append({"dir": str(d.relative_to(ws)), "files": n,
                                "manifest": _text(d / "MANIFEST.md", 100_000)})
    app = proj.data.get("app") or {}
    diff = _text(base / "02-construction" / "app.diff", 2_000_000) or ""
    return {
        "present": True, "active": proj.app_active,
        "backup": appmod.read_record(ws), "backups": backups,
        "intake": app.get("intake") or {}, "policies": app.get("policies") or {},
        "questionnaire": app.get("questionnaire"),
        "diff_files": _diff_files(diff), "has_diff": bool(diff.strip()),
        "docs": [str(f.relative_to(ws)) for f in sorted(base.rglob("*.md"))
                 if "backup" not in f.relative_to(base).parts],
    }
