"""Unit tests for the improvements from the 2026-09-23 workshop learnings.

Covers: follow-up ledger dedup + auto-resolve, gen-tests data coverage,
reset-identity verdicts/report, FK-count guard, Oracle internal-object filters and
the full-text advisory, and the global --conn/--config CLI flags.
"""
import os

import yaml

from dbmig import cli, followup as fu
from dbmig.commands import gen_tests, reset_identity as ri
from dbmig.conversion.ddl_split import count_foreign_keys
from dbmig.engines import oracle as ora
from dbmig.engines.base import ObjectUnit


# ---- follow-up ledger -----------------------------------------------------

def _ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(fu.config, "workspace_dir", lambda project: tmp_path)
    return fu.FollowUp("p")


def _items(led):
    return yaml.safe_load(led.path.read_text())["items"]


def test_record_dedups_open_item_on_repeat_failure(tmp_path, monkeypatch):
    led = _ledger(tmp_path, monkeypatch)
    led.record("validation", "test_failure", "DEMO.F [c1]", "first")
    led.record("validation", "test_failure", "DEMO.F [c1]", "second")
    items = _items(led)
    assert len(items) == 1
    assert items[0]["detail"] == "second" and items[0]["occurrences"] == 2


def test_resolve_transitions_only_matching_open_items(tmp_path, monkeypatch):
    led = _ledger(tmp_path, monkeypatch)
    led.record("validation", "test_failure", "DEMO.F [c1]", "x")
    led.record("validation", "test_failure", "DEMO.G [c1]", "y")
    led.record("validation", "data_mismatch", "DEMO.F [c1]", "z")
    assert led.resolve("test_failure", ["DEMO.F [c1]"]) == 1
    by = {(i["kind"], i["object"]): i for i in _items(led)}
    assert by[("test_failure", "DEMO.F [c1]")]["status"] == "resolved"
    assert "resolved_ts" in by[("test_failure", "DEMO.F [c1]")]
    assert by[("test_failure", "DEMO.G [c1]")]["status"] == "open"
    assert by[("data_mismatch", "DEMO.F [c1]")]["status"] == "open"
    assert led.open_count() == 2


def test_resolve_leaves_human_done_items_and_new_failure_reopens(tmp_path, monkeypatch):
    led = _ledger(tmp_path, monkeypatch)
    led.record("validation", "test_failure", "O [c1]", "x")
    items = _items(led)
    items[0]["status"] = "done"
    led._save(items)
    assert led.resolve("test_failure", ["O [c1]"]) == 0
    # a later failure of a closed item opens a NEW item (history is kept)
    led.record("validation", "test_failure", "O [c1]", "again")
    assert [i["status"] for i in _items(led)] == ["done", "open"]


def test_resolve_noop_without_ledger(tmp_path, monkeypatch):
    led = _ledger(tmp_path, monkeypatch)
    assert led.resolve("test_failure", ["x"]) == 0
    assert not led.path.exists()


# ---- gen-tests data coverage ----------------------------------------------

def test_referenced_tables_whole_word_and_comments_ignored():
    sql = """CREATE FUNCTION f RETURN NUMBER IS
      -- reads ORDERS_ARCHIVE only in a comment
      v NUMBER; BEGIN SELECT COUNT(*) INTO v FROM demo.orders o
      JOIN order_items i ON i.order_id = o.id; /* BOOKS */ RETURN v; END;"""
    refs = gen_tests.referenced_tables(sql, ["ORDERS", "ORDER_ITEMS", "BOOKS",
                                             "ORDERS_ARCHIVE", "ORD"])
    assert refs == ["ORDERS", "ORDER_ITEMS"]


def test_referenced_tables_keyword_named_table():
    sql = "SELECT a FROM dbo.Shopping ORDER BY a"
    assert gen_tests.referenced_tables(sql, ["Order", "Shopping"]) == ["Shopping"]
    assert gen_tests.referenced_tables("SELECT * FROM [dbo].[Order] o", ["Order"]) == ["Order"]
    assert gen_tests.referenced_tables('SELECT * FROM "Order"', ["Order"]) == ["Order"]


def test_coverage_levels():
    assert gen_tests.coverage_level({}) == gen_tests.NO_TABLES
    assert gen_tests.coverage_level({"A": 0, "B": 0}) == gen_tests.LOW_COVERAGE
    assert gen_tests.coverage_level({"A": 0, "B": 5}) == gen_tests.PARTIAL_COVERAGE
    assert gen_tests.coverage_level({"A": 3}) == gen_tests.FULL_COVERAGE
    # unknown count (-1) is not treated as empty
    assert gen_tests.coverage_level({"A": -1}) == gen_tests.FULL_COVERAGE


def test_run_tests_and_gen_tests_agree_on_low_coverage_label():
    from dbmig.commands import run_tests
    assert run_tests.LOW_COVERAGE == gen_tests.LOW_COVERAGE


# ---- reset-identity -------------------------------------------------------

def test_identity_verdict():
    assert ri.verdict(57, 58) == ri.OK
    assert ri.verdict(57, 1) == ri.NEEDS_SYNC
    assert ri.verdict(57, 57) == ri.NEEDS_SYNC      # next would collide
    assert ri.verdict(None, 100) == ri.OK          # empty table
    assert ri.verdict(57, None) == ri.UNKNOWN


def test_identity_report_is_runbook_ready():
    report = {
        "schema": "DEMO", "target_schema": "demo", "generated_at": "T",
        "applied": False,
        "identity_columns": [
            {"table": "books", "column": "id", "sequence": "demo.books_id_seq",
             "max_id": 57, "next_before": 1, "status": ri.NEEDS_SYNC}],
        "standalone_sequences": {"source": [], "target": []},
        "summary": {"identity_columns": 1, "ok": 0, "needs_sync": 1, "unknown": 0},
    }
    md = ri.render_md(report, "proj")
    assert md.startswith("> ⚠️ **AI-GENERATED")
    assert "--target-schema demo --project proj --apply" in md
    assert "| books | id | demo.books_id_seq | 57 | 1 | — | NEEDS_SYNC |" in md
    assert "None on either side" in md


def test_pg_identity_sql_is_parameterized():
    from dbmig.engines import postgresql as pg
    assert pg.IDENTITY_COLUMNS_SQL.count("%s") == 1
    assert pg.SEQUENCE_NEXT_SQL.count("%s") == 3
    assert pg.STANDALONE_SEQUENCES_SQL.count("%s") == 1


# ---- FK guard -------------------------------------------------------------

def test_count_foreign_keys():
    assert count_foreign_keys("") == 0
    assert count_foreign_keys("CREATE TABLE t (id bigint PRIMARY KEY);") == 0
    assert count_foreign_keys(
        'ALTER TABLE "D"."OI" ADD CONSTRAINT "FK1" FOREIGN KEY ("O") '
        'REFERENCES "D"."O" ("ID") ENABLE;') == 1
    assert count_foreign_keys("CREATE TABLE t (p int REFERENCES parent(id));") == 1
    assert count_foreign_keys(
        "CREATE TABLE t (CONSTRAINT fk FOREIGN KEY (p) REFERENCES parent (id), "
        "q int REFERENCES other(id));") == 2
    # comments, string literals and REFERENCES grants are not constraints
    assert count_foreign_keys(
        "-- FOREIGN KEY omitted\nCREATE TABLE t (n text DEFAULT 'REFERENCES x');\n"
        "GRANT SELECT, REFERENCES ON t TO app;") == 0


# ---- Oracle internal objects / full-text advisory -------------------------

def test_oracle_internal_filters_exclude_text_index_tables():
    for pat in ("DR$%", "MLOG$%", "RUPD$%", "SYS_IOT_OVER_%"):
        assert f"NOT LIKE '{pat}'" in ora.INTERNAL_TABLE_FILTER
        assert f"NOT LIKE '{pat}'" in ora.INTERNAL_OBJECT_FILTER


def test_fulltext_advisory_is_comment_only_and_first_in_unit():
    adv = ora.fulltext_advisory({"index": "BOOKS_TEXT_IDX", "table": "BOOKS",
                                 "indextype": "CTXSYS.CONTEXT",
                                 "parameters": "SYNC (ON COMMIT)",
                                 "columns": ["SEARCH_TEXT"]})
    lines = adv.splitlines()
    assert all(line.startswith("--") for line in lines)   # never executable DDL
    assert "fulltext_redesign" in lines[0] and "DR$BOOKS_TEXT_IDX$*" in adv
    unit = ObjectUnit(schema="DEMO", name="BOOKS",
                      components={"table": "CREATE TABLE books (id NUMBER)",
                                  "advisories": adv})
    assert unit.source_ddl.startswith("-- === ADVISORIES")
    assert count_foreign_keys(unit.source_ddl) == 0


# ---- CLI ------------------------------------------------------------------

def test_global_conn_and_config_flags_set_env(tmp_path, monkeypatch):
    monkeypatch.delenv("CONN_FILE", raising=False)
    monkeypatch.delenv("MIGRATION_CONFIG", raising=False)
    seen = {}
    monkeypatch.setattr(cli, "_dispatch",
                        lambda a: seen.update(cmd=a.command) or 0)
    rc = cli.main(["--conn", str(tmp_path / "c.yaml"),
                   "--config", str(tmp_path / "m.yaml"),
                   "reset-identity", "--schema", "DEMO", "--project", "p"])
    assert rc == 0 and seen["cmd"] == "reset-identity"
    assert os.environ["CONN_FILE"] == str((tmp_path / "c.yaml").resolve())
    assert os.environ["MIGRATION_CONFIG"] == str((tmp_path / "m.yaml").resolve())


def test_reset_identity_parser_defaults_to_dry_run():
    a = cli.build_parser().parse_args(["reset-identity", "--schema", "DEMO"])
    assert a.apply is False and a.target_schema is None


# ---- location guard -------------------------------------------------------

def test_location_guard(tmp_path, monkeypatch):
    root = cli.package_repo_root()
    assert root is not None and (root / "skills").is_dir()
    monkeypatch.delenv("CONN_FILE", raising=False)
    monkeypatch.chdir(root)
    assert cli._check_location() == 0                   # repo root
    monkeypatch.chdir(root / "scripts")
    assert cli._check_location() == 0                   # subfolder
    monkeypatch.chdir(tmp_path)
    assert cli._check_location() == 2                   # outside -> refuse
    monkeypatch.setenv("CONN_FILE", str(tmp_path / "c.yaml"))
    assert cli._check_location() == 0                   # explicit --conn honoured


# ---- Claude Code skill stubs stay in sync with skills/ --------------------

def test_claude_skill_stubs_are_current():
    import subprocess  # nosec B404 - runs a repo script with a fixed argv
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    r = subprocess.run([sys.executable, str(root / "scripts" / "sync-claude-skills.py"),
                        "--check"], capture_output=True, text=True)  # nosec B603 - fixed argv, sys.executable
    assert r.returncode == 0, r.stdout + r.stderr
    assert (root / "CLAUDE.md").read_text().count("@.kiro/steering/dbmig-aidlc.md") == 1


# ---- large-schema output + batching ---------------------------------------

def test_item_ok_is_capped_and_summarized(capsys, monkeypatch):
    from dbmig import console
    monkeypatch.setenv("DBMIG_ITEM_LIMIT", "3")
    for i in range(10):
        console.item_ok(f"t{i} pass")
    console.warn("failures always print")
    console.flush_items("r.md")
    out = capsys.readouterr().out
    assert out.count(" pass") == 3 and "failures always print" in out
    assert "7 more successful item(s) not shown" in out


def test_batch_by_size():
    from dbmig.engines.base import batch_by_size
    items = [("F", 100)] * 5 + [("F", 50000)] + [("P", 100)] * 3
    b = batch_by_size(items, lambda x: x[1], max_items=4, max_bytes=1000,
                      key_of=lambda x: x[0])
    assert [len(x) for x in b] == [4, 1, 1, 3]      # cap, tail, big alone, type change


def test_oracle_static_queries_embed_filters_verbatim():
    assert ora.INTERNAL_TABLE_FILTER in ora.SQL_LIST_TABLES
    assert ora.INTERNAL_TABLE_FILTER in ora.SQL_TABLES
    assert ora.INTERNAL_TABLE_FILTER in ora.SQL_DATATYPES
    assert ora.INTERNAL_OBJECT_FILTER in ora.SQL_OBJECT_COUNTS
    assert f"NOT ({ora.INTERNAL_OBJECT_FILTER})" in ora.SQL_EXCLUDED_COUNTS


def test_pg_drop_builders_quote_identifiers():
    from dbmig.engines import postgresql as pg
    assert pg.build_drop_server_sql('s"x') == 'DROP SERVER IF EXISTS "s""x" CASCADE'
    assert pg.build_drop_foreign_table_sql("st", "ft") == 'DROP FOREIGN TABLE IF EXISTS "st"."ft"'
    assert pg.build_drop_schema_sql("st") == 'DROP SCHEMA IF EXISTS "st" CASCADE'
