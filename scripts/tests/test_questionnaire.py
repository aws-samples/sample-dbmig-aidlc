"""Questionnaire intake: generation, parsing, apply, policy auto-resolution."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

from dbmig import cli, config, decisions as dec, gates, questionnaire as qn
from dbmig.conversion import prompt_builder as pb
from dbmig.project import load

PAIRS = ["oracle-to-postgresql", "oracle-to-mysql", "sqlserver-to-postgresql", "sqlserver-to-mysql"]


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DBMIG_MIGRATIONS_DIR", str(tmp_path / "migrations"))
    monkeypatch.setenv("CONN_FILE", str(tmp_path / "connections.yaml"))
    monkeypatch.setenv("MIGRATION_CONFIG", str(tmp_path / "migration-config.yaml"))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    root = tmp_path / "repo"
    repo = config.find_repo_root()
    (root / "skills").mkdir(parents=True)
    (root / "engines").symlink_to(repo / "engines")
    (root / "templates").symlink_to(repo / "templates")
    monkeypatch.setattr(config, "find_repo_root", lambda start=None: root)
    return tmp_path


def _answer(text: str, answers: dict) -> str:
    for qid, val in answers.items():
        text = re.sub(rf"(### {re.escape(qid)} .*?\n(?:.*\n)*?)\[Answer\]:[^\n]*",
                      lambda m: m.group(1) + f"[Answer]: {val}", text, count=1)
    return text


FILLED = {"Q1.1": "acme-ora", "Q1.2": "A", "Q2.4": "17.7", "Q3.1": "ora.example.internal",
          "Q3.3": "ORCLPDB1", "Q3.5": "migrator", "Q3.8": "pg.example.internal",
          "Q3.10": "appdb", "Q3.11": "app_owner", "Q4.1": "app, billing"}


# ---- sources ---------------------------------------------------------------

@pytest.mark.parametrize("pair", PAIRS)
def test_every_pair_has_valid_policy_questions(pair):
    secs = qn.load_sections(pair)
    ids = [q["id"] for _, q in qn._questions(secs)]
    assert len(ids) == len(set(ids))
    pol = [q for _, q in qn._questions(secs) if "policy" in (q.get("writes_to") or [])]
    assert pol, pair
    target = pair.split("-to-")[1]
    for q in pol:
        for o in q["options"]:
            for kind, opt in (o.get("resolves") or {}).items():
                ids = {x["id"] for x in dec.standard(kind, pair)["options"]}
                assert opt in ids, (pair, q["id"], kind, opt)
        if target == "mysql":
            assert "tsvector" not in yaml.safe_dump(q).lower()


def test_no_question_asks_for_a_password():
    for pair in PAIRS:
        for _, q in qn._questions(qn.load_sections(pair)):
            if "password" in q["key"]:
                assert q.get("validate") == "env_var"


# ---- parse / interpret -------------------------------------------------------

def test_parse_and_interpret():
    secs = qn.load_sections("oracle-to-postgresql")
    md = qn.render_round1(secs, {"Q2.1": "A", "Q2.3": "A"}, {}, pair="oracle-to-postgresql")
    md = _answer(md, {**FILLED, "Q7.1": "X) keep '' only in comments column", "Q3.6": "hunter2!"})
    md = md.replace("starting point\n\n[Answered by]:", "starting point\n\n[Answered by]: Alice", 1)
    answers, by = qn.parse(md)
    assert by["1"] == "Alice"
    ev = qn.evaluate(secs, answers)
    assert ev["values"]["schemas"] == ["app", "billing"]
    assert ev["values"]["source_port"] == 1521             # default_by engine
    assert ev["results"]["Q7.1"]["status"] == "other" and ev["other"][0][0] == "Q7.1"
    assert ("Q3.6", ev["results"]["Q3.6"]["error"]) in ev["invalid"]   # not an env var name
    assert "Q3.4" not in ev["applicable"]                  # SQL Server-only question
    assert ev["results"]["Q7.2"]["defaulted"]


# ---- CLI end to end -----------------------------------------------------------

def test_round1_new_check_apply(env, capsys):
    assert cli.main(["questionnaire", "new"]) == 0
    root_q = env / "repo" / "questionnaire.md"
    text = root_q.read_text()
    assert "pair=unknown" in text and "Q7.1" not in text
    root_q.write_text(_answer(text, {**FILLED, "Q2.1": "A", "Q2.3": "A"}))
    # first check adds the questions that depend on the engines (Oracle service name,
    # the pair's policies), keeps the answers, and reports the new required one
    capsys.readouterr()
    assert cli.main(["questionnaire", "check"]) == 1
    text = root_q.read_text()
    assert "pair=oracle-to-postgresql" in text and "Q7.1" in text and "acme-ora" in text
    out = capsys.readouterr()
    assert "missing: Q3.3" in out.out + out.err
    root_q.write_text(_answer(text, {"Q7.4": "A", "Q7.1": "B", "Q3.3": "ORCLPDB1"}))
    assert cli.main(["questionnaire", "check"]) == 0
    assert cli.main(["questionnaire", "check", "--apply"]) == 0
    ws = env / "migrations" / "acme-ora"
    assert (ws / "00-intake" / "questionnaire.md").exists() and not root_q.exists()
    cfg = yaml.safe_load((env / "migration-config.yaml").read_text())
    assert cfg["project"] == "acme-ora" and cfg["scope"]["schemas"] == ["APP", "BILLING"]
    assert cfg["intake"]["mode"] == "questionnaire"
    conn = yaml.safe_load((env / "connections.yaml").read_text())
    assert conn["source"]["password"] == "${ORA_PASSWORD}"
    assert conn["source"]["service_name"] == "ORCLPDB1" and conn["target"]["port"] == 5432
    p = load(ws)
    assert p.schemas == ["APP", "BILLING"] and p.data["intake"]["round1"] == "answered"
    assert p.policies["packages"]["resolves"] == {"naming_conflict": "schema_per_package"}
    assert p.policies["empty_string"]["choice"] == "B"
    # the policy answers a later decision; gates stay open
    d, _ = dec.raise_decision(p, phase="construction", kind="naming_conflict",
                              objects=["APP.P1.F", "APP.P1_F"])
    assert d["status"] == "decided" and d["via"] == "questionnaire" and d["choice"] == "schema_per_package"
    d2, _ = dec.raise_decision(p, phase="inception", kind="fulltext_redesign", objects=["APP.T"])
    assert d2["choice"] == "native"                         # Q7.8 blank -> recommended A
    assert gates.status(p, "inception") == "open"
    # a policy changed after the inception approval makes that gate stale
    (ws / "01-assessment").mkdir(parents=True, exist_ok=True)
    (ws / "01-assessment" / "inventory-APP.yaml").write_text("x: 1\n")
    (ws / "01-assessment" / "inventory-BILLING.yaml").write_text("x: 1\n")
    (ws / "01-assessment" / "migration-plan.md").write_text("# plan\n")
    gates.approve(p, "inception", by="u", via="chat")
    p.policies["empty_string"]["choice"] = "A"
    p.save()
    assert gates.status(p, "inception") == "stale"
    # policies reach the conversion context
    out = pb.write_shared_context(ws / "02-construction", pb.SCHEMA, env / "repo",
                                  pair="oracle-to-postgresql")
    body = (ws / out).read_text()
    assert "CUSTOMER DECISIONS" in body and "'' and NULL are distinct" in body


def test_apply_refuses_to_overwrite_existing_values(env, capsys):
    (env / "connections.yaml").write_text(yaml.safe_dump(
        {"source": {"engine": "oracle", "host": "old-host", "password": "s3cret-literal"}}))
    assert cli.main(["questionnaire", "new", "--pair", "oracle-to-postgresql"]) == 0
    f = env / "repo" / "questionnaire.md"
    text = f.read_text()
    assert "old-host" in text and "s3cret-literal" not in text   # prefilled, never the password
    f.write_text(_answer(text, {**FILLED, "Q3.6": "ORA_PW"}))
    capsys.readouterr()
    assert cli.main(["questionnaire", "check", "--apply"]) == 1
    err = capsys.readouterr().err
    assert "source.host" in err and "s3cret-literal" not in err and "<hidden>" in err
    assert not (env / "migration-config.yaml").exists()           # nothing half-applied
    assert cli.main(["questionnaire", "check", "--apply", "--overwrite"]) == 0
    assert yaml.safe_load((env / "connections.yaml").read_text())["source"]["password"] == "${ORA_PW}"


def test_new_refuses_to_replace_answers(env):
    assert cli.main(["questionnaire", "new", "--pair", "sqlserver-to-mysql"]) == 0
    f = env / "repo" / "questionnaire.md"
    assert "Q3.4" in f.read_text() and "Q3.3" not in f.read_text()
    f.write_text(_answer(f.read_text(), {"Q1.1": "x"}))
    assert cli.main(["questionnaire", "new"]) == 1
    assert cli.main(["questionnaire", "new", "--force"]) == 0


def test_round2_from_open_decisions(env):
    ws = env / "migrations" / "p2"
    p = load(ws)
    d1, _ = dec.raise_decision(p, phase="inception", kind="fulltext_redesign", objects=["APP.T"])
    d2, _ = dec.raise_decision(p, phase="inception", kind="case_insensitive_collation", objects=["APP"])
    assert cli.main(["questionnaire", "new", "--round", "2", "--project", "p2"]) == 0
    f = ws / qn.ROUND2
    text = f.read_text()
    assert d1["id"] in text and d2["id"] in text
    f.write_text(_answer(text, {d1["id"]: "B", d2["id"]: "X) citext only on email"})
                 .replace("Decisions\n\n[Answered by]:", "Decisions\n\n[Answered by]: Bob", 1))
    assert cli.main(["questionnaire", "check", "--round", "2", "--project", "p2", "--apply"]) == 0
    p.reload()
    a = dec.find(p, d1["id"])
    assert a["choice"] == "trigram" and a["by"] == "Bob" and a["via"] == "questionnaire"
    assert dec.find(p, d2["id"])["status"] == "open"            # Other -> assistant confirms
    # regenerating keeps only the still-open decision, with its earlier answer
    assert cli.main(["questionnaire", "new", "--round", "2", "--project", "p2"]) == 0
    text = f.read_text()
    assert f"### {d1['id']} " not in text and "citext only on email" in text


def test_round2_not_needed_without_open_decisions(env, capsys):
    load(env / "migrations" / "p3")
    capsys.readouterr()
    assert cli.main(["questionnaire", "new", "--round", "2", "--project", "p3"]) == 0
    assert "not needed" in capsys.readouterr().out


EXAMPLES = Path(__file__).resolve().parents[2] / "docs" / "examples" / "questionnaire"


@pytest.mark.parametrize("pair", PAIRS)
def test_blank_examples_match_the_generator(pair):
    """docs/examples/questionnaire/round1-blank-<pair>.md must be what
    `./dbmig questionnaire new --pair <pair>` writes (regenerate it when the
    question files change)."""
    secs = qn.load_sections(pair)
    src, tgt = pair.split("-to-")
    answers = {}
    for qid, val in (("Q2.1", src), ("Q2.3", tgt)):
        q = next(q for _, q in qn._questions(secs) if q["id"] == qid)
        answers[qid] = next(o["id"] for o in q["options"] if o.get("value") == val)
    expected = qn.render_round1(secs, answers, {}, pair=pair)
    assert (EXAMPLES / f"round1-blank-{pair}.md").read_text() == expected, (
        f"regenerate: ./dbmig questionnaire new --pair {pair} --force "
        f"--file docs/examples/questionnaire/round1-blank-{pair}.md")


def test_answered_example_is_complete():
    secs = qn.load_sections("oracle-to-postgresql")
    answers, by = qn.parse((EXAMPLES / "round1-answered-oracle-to-postgresql.md").read_text())
    ev = qn.evaluate(secs, answers)
    assert not ev["missing"] and not ev["invalid"] and by.get("1")
    assert all("password" not in a.lower() or a.isupper() for a in answers.values())
