"""Gate records, decisions and enforcement (project.yaml)."""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest
import yaml

from dbmig import cli, decisions as dec, gates
from dbmig.project import load, load_yaml

DISCLAIMER = "> ⚠ **AI-GENERATED — VALIDATE BEFORE USE.** review it.\n\n"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    mig = tmp_path / "migrations"
    monkeypatch.setenv("DBMIG_MIGRATIONS_DIR", str(mig))
    monkeypatch.setenv("CONN_FILE", str(tmp_path / "none-connections.yaml"))
    cfg = tmp_path / "migration-config.yaml"
    cfg.write_text(yaml.safe_dump({"project": "p1", "scope": {"schemas": ["APP"]},
                                   "strategy": {"mode": "full"}}))
    monkeypatch.setenv("MIGRATION_CONFIG", str(cfg))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    ws = mig / "p1"
    (ws / "01-assessment").mkdir(parents=True)
    return ws


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def _inception_ready(ws: Path) -> None:
    _write(ws / "01-assessment" / "inventory-APP.yaml", "schema: APP\n")
    _write(ws / "01-assessment" / "migration-plan.md", "# plan\n")


def _manifest(ws: Path, units, code=False) -> Path:
    name = ("code-manifest" if code else "manifest") + "-APP.yaml"
    return _write(ws / "02-construction" / name, yaml.safe_dump({"schema": "APP", "units": units}))


def _construction_ready(ws: Path) -> Path:
    m = _manifest(ws, [{"name": "T1", "status": "applied", "output_file": "ddl/APP/t1.sql"}])
    _write(ws / "02-construction" / "ddl" / "APP" / "t1.sql", "create table t1(x int);\n")
    return m


def _validation_ready(ws: Path) -> None:
    m = ws / "02-construction" / "manifest-APP.yaml"
    d = yaml.safe_load(m.read_text())
    for u in d["units"]:
        u["post_status"] = "applied"
    m.write_text(yaml.safe_dump(d))
    _write(ws / "03-validation" / "reconcile_report-APP.yaml",
           yaml.safe_dump({"results": [{"table": "T1", "status": "match"}]}))


def _ops_ready(ws: Path) -> None:
    for n in ("cutover-runbook.md", "rollback-plan.md", "monitoring.md"):
        _write(ws / "04-operations" / n, DISCLAIMER + f"# {n}\n")


def _cli(*argv) -> int:
    return cli.main(list(argv))


# ---- project.yaml ------------------------------------------------------------

def test_project_created_from_config_and_artifacts(env):
    _write(env / "02-construction" / "manifest-OTHER.yaml", "units: []\n")
    p = load(env)
    assert p.schemas == ["APP", "OTHER"]
    assert p.entry_path == "fresh" and p.data["pair"] == "oracle-to-postgresql"
    assert set(p.data["gates"]) == {"inception", "construction", "validation", "operations"}


def test_dms_sc_entry_detected(env):
    _write(env / "01-assessment" / "dms-sc-map-APP.json", "{}")
    assert load(env).entry_path == "dms-sc"


def test_unknown_keys_preserved_and_timestamps_stay_strings(env):
    p = load(env)
    p.data["custom"] = {"keep": 1}
    p.data["gates"]["inception"]["at"] = "2026-11-17T09:30:00.000Z"
    p.save()
    raw = (env / "project.yaml").read_text()
    assert "2026-11-17T09:30:00.000Z" in raw
    q = load(env)
    assert q.data["custom"] == {"keep": 1}
    assert isinstance(q.data["gates"]["inception"]["at"], str)
    # an unquoted timestamp written by hand also loads as a string
    (env / "project.yaml").write_text(raw.replace("'2026-11-17T09:30:00.000Z'",
                                                  "2026-11-17T09:30:00.000Z"))
    assert isinstance(load(env).data["gates"]["inception"]["at"], str)


# ---- blockers / approve ----------------------------------------------------

def test_inception_blockers_then_approve(env):
    p = load(env)
    b = gates.blockers(p, "inception")
    assert any("no inventory" in x for x in b) and any("migration-plan" in x for x in b)
    with pytest.raises(gates.GateError):
        gates.approve(p, "inception", by="u", via="chat")
    _inception_ready(env)
    v = gates.approve(p, "inception", by="u", via="chat", note="ok")
    assert v["status"] == "approved" and v["via"] == "chat"
    assert p.gate("inception")["history"][-1]["note"] == "ok"
    assert (env / "SIGN-OFF.md").exists()


def test_open_decision_blocks_and_answer_unblocks(env):
    _inception_ready(env)
    p = load(env)
    d, created = dec.raise_decision(p, phase="inception", kind="fulltext_redesign",
                                    objects=["APP.BOOKS"])
    assert created and d["status"] == "open"
    again, created2 = dec.raise_decision(p, phase="inception", kind="fulltext_redesign",
                                         objects=["app.books"])
    assert not created2 and again["id"] == d["id"]
    assert any("open decision" in x for x in gates.blockers(p, "inception"))
    with pytest.raises(dec.DecisionError):
        dec.answer(p, d["id"], "nope", by="u")
    dec.answer(p, d["id"], "native", by="u", via="chat")
    assert gates.blockers(p, "inception") == []


def test_later_gate_needs_earlier_and_stale_detection(env):
    _inception_ready(env)
    _construction_ready(env)
    p = load(env)
    assert any("'inception' is not approved" in x for x in gates.blockers(p, "construction"))
    gates.approve(p, "inception", by="u", via="chat")
    gates.approve(p, "construction", by="u", via="chat")
    # editing a covered file makes the gate stale ...
    _write(env / "01-assessment" / "migration-plan.md", "# plan v2\n")
    assert gates.status(p, "inception") == "stale"
    assert any(c.startswith("changed 01-assessment/migration-plan.md")
               for c in gates.changes_since(p, "inception"))
    v = gates.view(p, "inception")
    assert v["likely_cause"] and any("gate approve inception" in s for s in v["fix"])
    assert any("restore the file" in s for s in v["fix"])
    assert gates.view(p, "construction")["waits_on"] == "inception"   # later gate flagged
    assert any("stale" in x for x in gates.blockers(p, "validation"))
    # ... and re-approval clears it
    gates.approve(p, "inception", by="u", via="chat")
    assert gates.status(p, "inception") == "approved"


def test_post_status_does_not_stale_construction(env):
    _inception_ready(env)
    _construction_ready(env)
    p = load(env)
    gates.approve(p, "inception", by="u", via="chat")
    gates.approve(p, "construction", by="u", via="chat")
    _validation_ready(env)          # sets post_status + writes validation artifacts
    _write(env / "02-construction" / "apply_report_postdata-APP.yaml", "results: []\n")
    assert gates.status(p, "construction") == "approved"


def test_construction_unit_blockers(env):
    _inception_ready(env)
    p = load(env)
    gates.approve(p, "inception", by="u", via="chat")
    _manifest(env, [{"name": "T1", "status": "pending"}, {"name": "T2", "status": "converted"},
                    {"name": "T3", "status": "needs_human"}])
    b = " | ".join(gates.blockers(p, "construction"))
    assert "not converted/applied: T1" in b and "not applied: T2" in b and "T3" in b
    d, _ = dec.raise_decision(p, phase="construction", kind="needs_human", objects=["APP.T3"])
    dec.answer(p, d["id"], "skip", by="u")
    m = load_yaml(env / "02-construction" / "manifest-APP.yaml")
    assert [u["status"] for u in m["units"] if u["name"] == "T3"] == ["skipped"]
    assert "T3" not in " | ".join(gates.blockers(p, "construction"))


def test_followups_need_acknowledgement(env):
    _inception_ready(env)
    p = load(env)
    _write(env / "follow-up.yaml", yaml.safe_dump({"items": [
        {"phase": "inception", "kind": "note_x", "object": "A", "status": "open"},
        {"phase": "inception", "kind": "note_x", "object": "B", "status": "resolved"}]}))
    with pytest.raises(gates.GateError, match="note_x"):
        gates.approve(p, "inception", by="u", via="chat")
    v = gates.approve(p, "inception", by="u", via="chat", ack=["note_x"])
    assert v["acknowledged"] == ["note_x (1)"]


def test_validation_and_operations(env):
    _inception_ready(env)
    _construction_ready(env)
    p = load(env)
    gates.approve(p, "inception", by="u", via="chat")
    gates.approve(p, "construction", by="u", via="chat")
    b = gates.blockers(p, "validation")
    assert any("reconcile report" in x for x in b) and any("post-data" in x for x in b)
    _validation_ready(env)
    _write(env / "03-validation" / "equivalence-report-APP.yaml",
           yaml.safe_dump({"summary": {"failed": 2}}))
    assert gates.acknowledgements(p, "validation") == {"test_failure": 2}
    gates.approve(p, "validation", by="u", via="chat", ack_all=True)
    _write(env / "04-operations" / "cutover-runbook.md", "# no disclaimer\n")
    b = gates.blockers(p, "operations")
    assert any("disclaimer" in x for x in b) and any("rollback-plan" in x for x in b)
    _ops_ready(env)
    assert gates.approve(p, "operations", by="u", via="chat")["status"] == "approved"
    assert gates.next_gate(p) is None
    # reset-identity --apply at cutover rewrites its report: the gate must not go stale
    _write(env / "04-operations" / "identity-reset-APP.md", "# applied at cutover\n")
    assert gates.status(p, "operations") == "approved"


def test_reject_needs_reason_and_questionnaire_never_approves(env):
    _inception_ready(env)
    p = load(env)
    with pytest.raises(gates.GateError):
        gates.reject(p, "inception", by="u", reason=" ")
    with pytest.raises(gates.GateError):
        gates.approve(p, "inception", by="u", via="questionnaire")
    v = gates.reject(p, "inception", by="u", reason="plan incomplete", via="chat")
    assert v["status"] == "rejected" and "fingerprint" not in p.gate("inception")


def test_handwritten_sign_off_is_not_overwritten(env):
    _inception_ready(env)
    _write(env / "SIGN-OFF.md", "# hand written\n")
    p = load(env)
    gates.approve(p, "inception", by="u", via="chat")
    assert (env / "SIGN-OFF.md").read_text() == "# hand written\n"


# ---- CLI -----------------------------------------------------------------

def test_cli_approve_refused_without_chat_channel(env):
    _inception_ready(env)
    assert _cli("gate", "approve", "inception", "--project", "p1") == 2
    assert load(env).gate("inception")["status"] == "open"
    assert _cli("gate", "approve", "inception", "--project", "p1",
                "--approved-by", "Dong", "--via", "chat") == 0
    g = load(env).gate("inception")
    assert g["status"] == "approved" and g["by"] == "Dong" and g["via"] == "chat"


def test_cli_status_json_and_decisions(env):
    _inception_ready(env)
    assert _cli("decision", "raise", "--project", "p1", "--phase", "inception",
                "--kind", "custom", "--objects", "APP.X", "--question", "Which?",
                "--option", "a=First", "--option", "b=Second", "--recommend", "b") == 0
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert _cli("gate", "status", "--project", "p1", "--json") == 0
    data = json.loads(buf.getvalue())
    assert data["next"] == "inception"
    assert any("open decision" in b for b in data["gates"][0]["blockers"])
    assert _cli("decision", "answer", "D-001", "--choice", "b", "--project", "p1") == 2
    assert _cli("decision", "answer", "D-001", "--choice", "b", "--project", "p1",
                "--approved-by", "Dong", "--via", "chat") == 0
    assert load(env).decisions[0]["choice"] == "b"


def test_cli_reject_requires_reason(env):
    with pytest.raises(SystemExit):
        _cli("gate", "reject", "inception", "--project", "p1")


# ---- enforcement ---------------------------------------------------------

def test_precheck_warns_by_default_and_refuses_when_enforced(env, tmp_path, capsys):
    msg = gates.precheck("convert-schema", env, enforce=False)
    assert msg and "inception" in msg
    assert gates.precheck("inventory", env, enforce=False) is None
    assert gates.precheck("reset-identity", env, enforce=False, apply=False) is None
    cfg = Path(tmp_path / "migration-config.yaml")
    cfg.write_text(yaml.safe_dump({"project": "p1", "scope": {"schemas": ["APP"]},
                                   "run": {"enforce_gates": True}}))
    capsys.readouterr()
    assert _cli("convert-schema", "--schema", "APP", "--project", "p1") == 2
    assert "refused: gate 'inception'" in capsys.readouterr().err
    _inception_ready(env)
    gates.approve(load(env), "inception", by="u", via="chat")
    assert gates.precheck("convert-schema", env, enforce=True) is None


# ---- auto decisions --------------------------------------------------------

def test_auto_raise_records_and_dedupes(env):
    d1 = dec.auto_raise("p1", phase="inception", kind="case_insensitive_collation",
                        objects=["APP"], raised_by="step:inventory")
    d2 = dec.auto_raise("p1", phase="inception", kind="case_insensitive_collation",
                        objects=["APP"], raised_by="step:inventory")
    assert d1["id"] == d2["id"] == "D-001"
    assert len(load(env).decisions) == 1


def test_stale_reason_names_the_changed_decision(env):
    _inception_ready(env)
    p = load(env)
    d, _ = dec.raise_decision(p, phase="inception", kind="fulltext_redesign", objects=["APP.T"])
    dec.answer(p, d["id"], "native", by="u")
    gates.approve(p, "inception", by="u", via="chat")
    dec.answer(p, d["id"], "trigram", by="u")
    (r,) = gates.check(p, "inception")["reasons"]
    assert r["kind"] == "decision_changed" and "decided (native) -> decided (trigram)" in r["text"]
    assert any("decision answer" in s for s in gates.view(p, "inception")["fix"])

