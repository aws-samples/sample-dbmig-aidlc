"""``dbmig questionnaire new|check`` — optional markdown intake.

    ./dbmig questionnaire new   [--project P] [--pair oracle-to-postgresql] [--force]
    ./dbmig questionnaire check [--project P] [--apply] [--overwrite] [--json]
    ./dbmig questionnaire new   --round 2 --project P
    ./dbmig questionnaire check --round 2 --project P [--apply]

Round 1 goes to migrations/<P>/00-intake/questionnaire.md when the project is known,
else ./questionnaire.md (git-ignored; moved into the workspace on --apply).
``check`` only reports; ``--apply`` writes migration-config.yaml, the password-free
fields of connections.yaml and project.yaml. Existing values are not overwritten
without --overwrite (the changes are listed first).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .. import config, console, decisions as dec, questionnaire as qn
from ..project import exists, load, load_yaml, now, whoami

_MARK_PAIR = re.compile(r"round=1 pair=([\w-]+)")


def _explicit_ws(args) -> Optional[Path]:
    if getattr(args, "dir", None):
        return Path(args.dir).expanduser().resolve()
    name = (getattr(args, "qproject", None) or "").strip()
    if not name and config.migration_config_path().exists():
        try:
            name = str(config.load_migration_config().get("project") or "").strip()
        except config.ConfigError:
            name = ""
    return config.workspace_dir(config.sanitize_project(name)) if name else None


def _root_file() -> Path:
    return config.find_repo_root() / qn.ROOT_FILE


def _round1_file(args) -> Path:
    if getattr(args, "file", None):
        return Path(args.file).expanduser().resolve()
    ws = _explicit_ws(args)
    if ws and (ws / qn.ROUND1).exists():
        return ws / qn.ROUND1
    if _root_file().exists() or not ws:
        return _root_file()
    return ws / qn.ROUND1


def _read(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        d = load_yaml(path) or {}
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _existing_pair() -> Optional[str]:
    if not config.connections_path().exists():
        return None
    p = config.active_pair()
    return p if (config.find_repo_root() / "engines" / p).is_dir() else None


# ---- new ---------------------------------------------------------------------

def run_new(args) -> int:
    if args.round == 2:
        return _new_round2(args)
    path = _round1_file(args)
    if path.exists():
        answers, _ = qn.parse(path.read_text())
        if any(v.strip() for v in answers.values()) and not args.force:
            console.err(f"{path} already has answers; run ./dbmig questionnaire check "
                        "(or --force to start over)")
            return 1
    pair = args.pair or _existing_pair()
    if pair and not (config.find_repo_root() / "engines" / pair).is_dir():
        console.err(f"unknown engine pair {pair}")
        return 2
    sections = qn.load_sections(pair)
    answers = qn.prefill(sections, _read(config.connections_path()),
                         _read(config.migration_config_path()))
    if pair:
        src, tgt = pair.split("-to-")
        for qid, val in (("Q2.1", src), ("Q2.3", tgt)):
            q = next(q for _, q in qn._questions(sections) if q["id"] == qid)
            answers[qid] = next(o["id"] for o in q["options"] if o.get("value") == val)
    ws = _explicit_ws(args)
    if ws and "Q1.1" not in answers:
        answers["Q1.1"] = ws.name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(qn.render_round1(sections, answers, {}, pair=pair))
    n = len(qn.evaluate(sections, answers)["applicable"])
    console.ok(f"wrote {path} ({n} questions"
               + (f", {len(answers)} pre-filled from existing files" if answers else "") + ")")
    console.info("Answer it, then run ./dbmig questionnaire check"
                 + (f" --project {ws.name}" if ws else ""))
    return 0


def _new_round2(args) -> int:
    ws = _explicit_ws(args)
    if not ws:
        console.err("round 2 needs --project (the migration workspace)")
        return 2
    proj = load(ws)
    opened = dec.open_decisions(proj)
    if not opened:
        console.ok("no open decisions: round 2 is not needed")
        return 0
    f = ws / qn.ROUND2
    old = {}
    if f.exists():
        old, by = qn.parse(f.read_text())
        old["_by"] = by.get("D", "")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(qn.render_round2(proj.name, opened, old))
    intake = proj.data.setdefault("intake", {})
    intake["round2"] = "open"
    proj.save()
    console.ok(f"wrote {f} ({len(opened)} decision(s))")
    return 0


# ---- check ---------------------------------------------------------------------

def _mask(lines):
    return [re.sub(r"(password: ).*", r"\1<hidden>", ln) for ln in lines]


def _plan_file(path: Path, upd: Dict[str, Any], template: Optional[Path]):
    """(merged dict or None when nothing changes, overwritten keys) for ``path``."""
    if path.exists():
        base = _read(path)
        merged = qn.merge(base, upd)
        if merged == base:
            return None, []
        return merged, _mask(qn.changed_keys(base, merged))
    base = _read(template) if template and template.exists() else {}
    return qn.merge(base, upd), []


def _write_file(path: Path, merged: Optional[Dict[str, Any]], label: str) -> None:
    if merged is None:
        return
    path.write_text(f"# {label} — written by ./dbmig questionnaire check --apply\n"
                    + yaml.safe_dump(merged, sort_keys=False))


def _intake_md(ws: Path, ev: Dict[str, Any], pair: Optional[str], src: str) -> None:
    f = ws / "00-intake" / "intake.md"
    if f.exists() and "questionnaire check" not in f.read_text()[:300]:
        return
    v = ev["values"]
    lines = [f"# Intake — {ws.name}", "", "<!-- written by ./dbmig questionnaire check -->", "",
             f"- Source of answers: `{src}`",
             f"- Entry path: {v.get('entry_path')}", f"- Engine pair: {pair}",
             f"- Source: {v.get('source_engine')} {v.get('source_version') or '(detect)'} "
             f"at {v.get('source_host')}", f"- Target: {v.get('target_engine')} "
             f"{v.get('target_version')} at {v.get('target_host')} / {v.get('target_database')}",
             f"- Schemas: {', '.join(v.get('schemas') or [])}",
             f"- Strategy: {v.get('strategy')}; test data: {v.get('data_load')}",
             f"- Gate approvers: {v.get('approvers') or '(whoever runs the migration)'}", "",
             "Passwords are not stored here; see connections.yaml for the variable names."]
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(lines) + "\n")


def run_check(args) -> int:
    if args.round == 2:
        return _check_round2(args)
    path = _round1_file(args)
    if not path.exists():
        console.err(f"no questionnaire at {path} (create one with ./dbmig questionnaire new)")
        return 2
    text = path.read_text()
    answers, by = qn.parse(text)
    m = _MARK_PAIR.search(text)
    file_pair = m.group(1) if m and m.group(1) != "unknown" else None
    ev = qn.evaluate(qn.load_sections(file_pair), answers)
    pair = qn.pair_from(ev["values"]) or file_pair
    sections = qn.load_sections(pair)
    added = 0
    if pair != file_pair:
        before = len(ev["applicable"])
        path.write_text(qn.render_round1(sections, answers, by, pair=pair))
        ev = qn.evaluate(sections, answers)
        added = len(ev["applicable"]) - before
    else:
        ev = qn.evaluate(sections, answers)
    report = {"file": str(path), "pair": pair, "questions": len(ev["applicable"]),
              "added_policy_questions": added,
              "missing": ev["missing"], "invalid": [{"id": i, "error": e} for i, e in ev["invalid"]],
              "other": [{"id": i, "answer": a} for i, a in ev["other"]]}
    if args.json and not args.apply:
        print(json.dumps(report, indent=2))
        return 0 if not (ev["missing"] or ev["invalid"]) else 1
    console.heading(f"Questionnaire round 1 — {path}")
    if added:
        console.info(f"added {added} conversion-policy question(s) for {pair}; answer them "
                     "(blank = recommended)")
    for qid in ev["missing"]:
        console.warn(f"missing: {qid}")
    for qid, e in ev["invalid"]:
        console.err(f"invalid: {qid}: {e}")
    for qid, a in ev["other"]:
        console.info(f"other (assistant to confirm with the user): {qid}: {a}")
    ok = not (ev["missing"] or ev["invalid"])
    if ok:
        console.ok(f"{len(ev['applicable'])} question(s) answered")
    if not args.apply:
        return 0 if ok else 1
    if not ok:
        console.err("not applied: answer the missing/invalid questions first")
        return 1
    return _apply_round1(args, path, sections, ev, by, pair)


def _apply_round1(args, path: Path, sections, ev, by, pair) -> int:
    v = ev["values"]
    ws = config.workspace_dir(config.sanitize_project(v["project"]))
    src = qn.ROUND1
    out = qn.build_outputs(sections, ev, source=src, by={k: x for k, x in by.items() if x},
                           default_by=whoami(), when=now())
    root = config.find_repo_root()
    out["config"].setdefault("intake", {})["mode"] = "questionnaire"
    cfg_path, conn_path = config.migration_config_path(), config.connections_path()
    cfg_new, cfg_chg = _plan_file(cfg_path, out["config"],
                                  root / "templates" / "migration-config.example.yaml")
    conn_new, conn_chg = _plan_file(conn_path, out["connections"], None)
    if (cfg_chg or conn_chg) and not args.overwrite:
        for p, chg in ((cfg_path, cfg_chg), (conn_path, conn_chg)):
            if chg:
                console.err(f"{p} has different values:\n  " + "\n  ".join(chg))
        console.err("nothing applied; re-run with --overwrite to replace them")
        return 1
    _write_file(cfg_path, cfg_new, "dbmig-aidlc migration config")
    _write_file(conn_path, conn_new, "dbmig-aidlc connections (no passwords; ${VAR} references)")
    proj = load(ws, name=ws.name)
    d = proj.data
    d["pair"] = pair or d.get("pair")
    if v.get("entry_path"):
        d["entryPath"] = v["entry_path"]
    if v.get("schemas"):
        d["schemas"] = [str(s).upper() for s in v["schemas"]]
    if v.get("strategy"):
        d["strategy"] = v["strategy"]
    d.setdefault("policies", {}).update(out["policies"])
    intake = d.setdefault("intake", {})
    intake.update({"mode": "questionnaire", "round1": "answered", "answers": out["intake"]})
    proj.save()
    target = ws / qn.ROUND1
    if path.resolve() != target.resolve():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text())
        path.unlink()
        console.info(f"moved the questionnaire to {target}")
    _intake_md(ws, ev, pair, src)
    resolved = dec.resolve_by_policies(proj)
    console.ok(f"applied: {config.migration_config_path().name}, {config.connections_path().name}, "
               f"{proj.file} ({len(out['policies'])} policies)")
    for x in resolved:
        console.info(f"{x['id']} ({x['kind']}) answered by policy {x['policy']}")
    console.info("next: ./dbmig test-connection --side both (export the password variables first)")
    return 0


def _check_round2(args) -> int:
    ws = _explicit_ws(args)
    if not ws or not exists(ws):
        console.err("round 2 needs --project (the migration workspace)")
        return 2
    f = Path(args.file).expanduser() if getattr(args, "file", None) else ws / qn.ROUND2
    if not f.exists():
        console.err(f"no round-2 questionnaire at {f}")
        return 2
    proj = load(ws)
    answers, by = qn.parse(f.read_text())
    who = by.get("D") or whoami()
    missing, invalid, other, ready = [], [], [], []
    for d in dec.open_decisions(proj):
        if d["id"] not in answers:
            continue
        r = qn.round2_choice(d, answers.get(d["id"], ""))
        if r["status"] == "missing":
            missing.append(d["id"])
        elif r["status"] == "invalid":
            invalid.append((d["id"], r["error"]))
        elif r["status"] == "other":
            other.append((d["id"], r["other"]))
        else:
            ready.append((d, r["value"]))
    console.heading(f"Questionnaire round 2 — {f}")
    for i in missing:
        console.warn(f"missing: {i}")
    for i, e in invalid:
        console.err(f"invalid: {i}: {e}")
    for i, a in other:
        console.info(f"other (assistant to confirm with the user): {i}: {a}")
    console.info(f"{len(ready)} decision(s) answered")
    if not args.apply:
        return 0 if not (missing or invalid) else 1
    for d, choice in ready:
        dec.answer(proj, d["id"], choice, by=who, via="questionnaire",
                   rationale=f"answered in {qn.ROUND2}")
        console.ok(f"{d['id']} -> {dec.option_label(d)}")
    if not dec.open_decisions(proj):
        proj.data.setdefault("intake", {})["round2"] = "answered"
        proj.save()
    return 0 if not (missing or invalid) else 1
