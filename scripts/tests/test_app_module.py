"""Application modernization module: gates, backup (git / file copy), questionnaire, review."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from dbmig import appmod, cli, config, gates, questionnaire as qn
from dbmig.project import APP_GATED_PHASES, GATED_PHASES, load

DISCLAIMER = "> ⚠ **AI-GENERATED — VALIDATE BEFORE USE.** review it.\n\n"
HAS_GIT = shutil.which("git") is not None


@pytest.fixture()
def env(tmp_path, monkeypatch):
    mig = tmp_path / "migrations"
    monkeypatch.setenv("DBMIG_MIGRATIONS_DIR", str(mig))
    monkeypatch.setenv("CONN_FILE", str(tmp_path / "none-connections.yaml"))
    cfg = tmp_path / "migration-config.yaml"
    cfg.write_text(yaml.safe_dump({"project": "p1", "scope": {"schemas": ["APP"]}}))
    monkeypatch.setenv("MIGRATION_CONFIG", str(cfg))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    ws = mig / "p1"
    (ws / "01-assessment").mkdir(parents=True)
    return ws


def _w(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def _app(tmp_path: Path) -> Path:
    app = tmp_path / "app"
    _w(app / "src" / "Main.java", "class Main { String sql = \"select sysdate from dual\"; }\n")
    _w(app / "pom.xml", "<project/>\n")
    _w(app / "target" / "Main.class", "binary\n")
    _w(app / "src" / "local.properties", "db.url=x\n")
    return app


def _git(app: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(app), *args], check=True, capture_output=True)


def _init_git(app: Path) -> None:
    _git(app, "init", "-q")
    _git(app, "config", "user.email", "t@example.com")
    _git(app, "config", "user.name", "t")
    _w(app / ".gitignore", "target/\nsrc/local.properties\n")
    _git(app, "add", "-A")
    _git(app, "commit", "-qm", "base")


def _approve(ws: Path, phase: str) -> int:
    return cli.main(["gate", "approve", phase, "--project", ws.name, "--approved-by", "Ana",
                     "--via", "chat"])


def _app_inception_ready(ws: Path) -> None:
    _w(ws / "05-application" / "00-intake" / "app-intake.md", "# App intake\n")
    _w(ws / "05-application" / "01-assessment" / "change-plan.md", "# Change plan\n")


# ---- gates ------------------------------------------------------------------

def test_app_gates_appear_only_after_the_app_intake(env):
    proj = load(env)
    assert proj.gated_phases == GATED_PHASES
    assert gates.next_gate(proj) == "inception"
    _app_inception_ready(env)
    proj = load(env)
    assert proj.gated_phases == GATED_PHASES + APP_GATED_PHASES
    assert "app-inception" in proj.data["gates"]


def test_app_inception_blocks_without_change_plan_and_warns_on_db_gate(env):
    _w(env / "05-application" / "00-intake" / "app-intake.md", "# App intake\n")
    v = gates.view(load(env), "app-inception")
    assert any("change-plan.md" in b for b in v["blockers"])
    assert any("database Construction gate" in w for w in v["warnings"])
    assert v["group"] == "application"


def test_app_inception_approve_then_stale_on_change_plan_edit(env, capsys):
    _app_inception_ready(env)
    assert _approve(env, "app-inception") == 0
    proj = load(env)
    assert gates.status(proj, "app-inception") == "approved"
    # the database gates are independent
    assert gates.status(proj, "inception") == "open"
    _w(env / "05-application" / "01-assessment" / "change-plan.md", "# Change plan v2\n")
    v = gates.view(load(env), "app-inception")
    assert v["status"] == "stale"
    assert any("change-plan.md" in c for c in v["changes"])
    assert any("gate approve app-inception" in s for s in v["fix"])


def test_app_construction_needs_backup_and_diff(env):
    _app_inception_ready(env)
    _approve(env, "app-inception")
    _w(env / "05-application" / "02-construction" / "conversion-log.md", "# log\n")
    b = gates.blockers(load(env), "app-construction")
    assert any("no application backup" in x for x in b)
    assert any("app.diff" in x for x in b)


def test_app_operations_needs_disclaimer(env):
    _app_inception_ready(env)
    _w(env / "05-application" / "04-operations" / "app-cutover.md", "# cutover\n")
    b = gates.blockers(load(env), "app-operations")
    assert any("disclaimer" in x for x in b)
    _w(env / "05-application" / "04-operations" / "app-cutover.md", DISCLAIMER + "# cutover\n")
    assert not any("disclaimer" in x for x in gates.blockers(load(env), "app-operations"))


def test_sign_off_lists_app_gates(env):
    _app_inception_ready(env)
    _approve(env, "app-inception")
    text = (env / "SIGN-OFF.md").read_text()
    assert "Application — Assessment & Change Plan" in text


# ---- backup -------------------------------------------------------------------

def test_non_git_app_uses_file_copy_and_skips_build_output(env, tmp_path):
    app = _app(tmp_path)
    rec = appmod.make_backup(env, app, requested="auto")
    assert rec["mode"] == "file-copy"
    dest = env / rec["backup_dir"]
    assert (dest / "src" / "Main.java").exists() and (dest / "pom.xml").exists()
    assert not (dest / "target").exists()
    assert (dest / "MANIFEST.md").exists()
    assert appmod.read_record(env)["mode"] == "file-copy"


def test_git_requested_but_not_possible_falls_back_to_file_copy(env, tmp_path):
    app = _app(tmp_path)
    rec = appmod.make_backup(env, app, requested="git")
    assert rec["mode"] == "file-copy"
    assert "falling back to a file copy" in rec["reason"]
    assert rec["files_copied"] >= 2


@pytest.mark.skipif(not HAS_GIT, reason="git not installed")
def test_clean_git_app_uses_git_and_copies_ignored_files(env, tmp_path):
    app = _app(tmp_path)
    _init_git(app)
    rec = appmod.make_backup(env, app, requested="auto", scope=["src", "pom.xml"])
    assert rec["mode"] == "git"
    assert len(rec["git"]["commit"]) == 40
    dest = env / rec["backup_dir"]
    # git cannot restore an ignored file, so it is copied; tracked files are not
    assert (dest / "src" / "local.properties").exists()
    assert not (dest / "src" / "Main.java").exists()


@pytest.mark.skipif(not HAS_GIT, reason="git not installed")
def test_dirty_git_app_falls_back_to_file_copy(env, tmp_path):
    app = _app(tmp_path)
    _init_git(app)
    _w(app / "src" / "Main.java", "class Main { /* uncommitted */ }\n")
    rec = appmod.make_backup(env, app, requested="git")
    assert rec["mode"] == "file-copy"
    assert "uncommitted" in rec["reason"]
    assert (env / rec["backup_dir"] / "src" / "Main.java").read_text().startswith("class Main { /*")


@pytest.mark.skipif(not HAS_GIT, reason="git not installed")
def test_git_mode_construction_gate_goes_stale_when_app_files_change(env, tmp_path):
    app = _app(tmp_path)
    _init_git(app)
    _app_inception_ready(env)
    _approve(env, "app-inception")
    assert cli.main(["app-backup", "--project", env.name, "--app", str(app)]) == 0
    _w(app / "src" / "Main.java", "class Main { String sql = \"select localtimestamp\"; }\n")
    _w(env / "05-application" / "02-construction" / "conversion-log.md", "# log\n")
    _w(env / "05-application" / "02-construction" / "app.diff", "diff --git a/src/Main.java b/src/Main.java\n")
    assert _approve(env, "app-construction") == 0
    assert gates.status(load(env), "app-construction") == "approved"
    # an edit after approval, without regenerating app.diff, is still seen
    _w(app / "src" / "Main.java", "class Main { String sql = \"select now()\"; }\n")
    v = gates.view(load(env), "app-construction")
    assert v["status"] == "stale"
    assert any("git diff against the base commit" in c for c in v["changes"])


def test_backup_refuses_workspace_inside_app(tmp_path):
    app = _app(tmp_path)
    with pytest.raises(appmod.BackupError):
        appmod.make_backup(app / "migrations" / "p", app)


def test_app_backup_cli_shows_existing_record(env, tmp_path, capsys):
    app = _app(tmp_path)
    assert cli.main(["app-backup", "--project", env.name, "--app", str(app), "--mode", "file-copy"]) == 0
    assert cli.main(["app-backup", "--project", env.name]) == 0
    assert "already recorded" in capsys.readouterr().out


def test_app_backup_warns_before_app_inception_approval(env, tmp_path, capsys):
    app = _app(tmp_path)
    cli.main(["app-backup", "--project", env.name, "--app", str(app)])
    err = capsys.readouterr()
    assert "app-inception" in (err.out + err.err)


# ---- questionnaire ---------------------------------------------------------------

def _answer(text: str, answers: dict) -> str:
    for qid, val in answers.items():
        text = re.sub(rf"(### {re.escape(qid)} .*?\n(?:.*\n)*?)\[Answer\]:[^\n]*",
                      lambda m: m.group(1) + f"[Answer]: {val}", text, count=1)
    return text


@pytest.mark.parametrize("pair", ["oracle-to-postgresql", "oracle-to-mysql",
                                  "sqlserver-to-postgresql", "sqlserver-to-mysql"])
def test_every_pair_has_app_policy_questions(pair):
    secs = qn.load_app_sections(pair)
    ids = [q["id"] for s in secs for q in s["questions"]]
    assert len(ids) == len(set(ids))
    assert any(s["id"] == "5" for s in secs), "pair section missing"
    for s in secs:
        for q in s["questions"]:
            assert "password" not in q["text"].lower() or "never" in q["text"].lower()


def test_app_questionnaire_new_check_apply(env, capsys):
    assert cli.main(["questionnaire", "new", "--module", "app", "--project", env.name,
                     "--pair", "oracle-to-postgresql"]) == 0
    f = env / qn.APP_FILE
    assert cli.main(["questionnaire", "check", "--module", "app", "--project", env.name]) == 1
    f.write_text(_answer(f.read_text(), {"Q1.1": "/srv/app", "Q1.2": "src, pom.xml",
                                         "Q3.1": "B", "Q5.1": "B"}))
    assert cli.main(["questionnaire", "check", "--module", "app", "--project", env.name,
                     "--apply"]) == 0
    proj = load(env)
    app = proj.data["app"]
    assert app["intake"]["app_dir"] == "/srv/app"
    assert app["intake"]["scope"] == ["src", "pom.xml"]
    assert app["intake"]["backup_mode"] == "git"
    assert app["policies"]["app_case_insensitive"]["choice"] == "B"
    assert app["policies"]["app_error_codes"].get("defaulted")
    # application policies never land in the database policies (no DB gate goes stale)
    assert "app_case_insensitive" not in (proj.data.get("policies") or {})
    md = (env / qn.APP_POLICIES).read_text()
    assert "ILIKE" in md and "/srv/app" in md


def test_app_policy_change_stales_app_inception_only(env):
    _app_inception_ready(env)
    proj = load(env)
    proj.app["policies"] = {"app_error_codes": {"choice": "A"}}
    proj.save()
    _approve(env, "app-inception")
    proj = load(env)
    proj.app["policies"]["app_error_codes"]["choice"] = "B"
    proj.save()
    v = gates.view(load(env), "app-inception")
    assert v["status"] == "stale"
    assert any("app_error_codes" in c for c in v["changes"])


# ---- review -------------------------------------------------------------------

def test_review_has_application_page(env, tmp_path):
    from dbmig.review.build import build
    _app_inception_ready(env)
    _w(env / "05-application" / "02-construction" / "app.diff",
       "diff --git a/src/A.java b/src/A.java\n--- a/src/A.java\n+++ b/src/A.java\n@@ -1 +1 @@\n-old\n+new\n")
    out = tmp_path / "site"
    build(env, out)
    html = (out / "application.html").read_text()
    assert "src/A.java" in html and "+1" in html and "-1" in html
    assert "No backup recorded yet" in html
    assert 'href="application.html"' in (out / "index.html").read_text()
    assert "Application modernization" in (out / "gates.html").read_text()


def test_review_without_app_module_has_no_application_page(env, tmp_path):
    from dbmig.review.build import build
    out = tmp_path / "site"
    build(env, out)
    assert not (out / "application.html").exists()
    assert "application.html" not in (out / "index.html").read_text()


def test_sample_app_diffs_parse():
    root = config.find_repo_root()
    from dbmig.review.collect import _diff_files
    for s in ("sample-run-oracle-to-pg", "sample-run-sqlserver-to-pg"):
        f = root / s / "05-application" / "02-construction" / "app.diff"
        files = _diff_files(f.read_text())
        assert files and all(x["path"] and x["path"] != "?" for x in files)


def test_app_examples_match_the_generator_and_are_complete():
    root = config.find_repo_root()
    ex = root / "docs" / "examples" / "questionnaire"
    secs = qn.load_app_sections("oracle-to-postgresql")
    assert (ex / "app-blank-oracle-to-postgresql.md").read_text() == \
        qn.render_app(secs, {}, {}, pair="oracle-to-postgresql")
    answers, by = qn.parse((ex / "app-answered-oracle-to-postgresql.md").read_text())
    ev = qn.evaluate(secs, answers)
    assert not ev["missing"] and not ev["invalid"] and ev["other"]
