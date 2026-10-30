import pytest

from dbmig.conversion import prompt_builder as pb
from dbmig.engines.base import ObjectUnit, assert_identifier


def test_context_is_pair_aware_mysql():
    ctx = pb.build_context(pair="oracle-to-mysql")
    assert "skills/oracle-to-mysql-playbook/references/" in ctx
    assert "PostgreSQL datatype reference" not in ctx


def test_datatype_header_names_actual_source():
    # The datatype-reference header must name the active pair's SOURCE engine,
    # not a hardcoded "Oracle" (regression: SQL Server pairs showed "Oracle -> ...").
    ctx = pb.build_context(pair="sqlserver-to-postgresql")
    assert "SQL Server -> postgresql datatype reference" in ctx
    assert "Oracle -> postgresql datatype reference" not in ctx


def test_unit_prompt_source_aware_sqlserver():
    u = ObjectUnit("dbo", "Orders", {"table": "CREATE TABLE [dbo].[Orders] (...)"}, 5)
    p = pb.build_unit_prompt(u, pair="sqlserver-to-postgresql")
    assert "SOURCE DDL (SQL Server)" in p
    # the task instruction must name the right source + target, not hardcoded Oracle
    task = p.split("=== TASK ===")[1]
    assert "SQL Server" in task and "PostgreSQL" in task and "Oracle" not in task


def test_instruction_targets():
    assert "MySQL" in pb._instruction("Oracle", "mysql")
    assert "PostgreSQL" in pb._instruction("SQL Server", "postgresql")


def test_retry_prompt_includes_error():
    out = pb.build_retry_prompt("ORIGINAL", "CREATE x", "ERROR 42: bad type", 2, 3)
    assert "RETRY 2/3" in out and "ERROR 42: bad type" in out and "CREATE x" in out


def test_assert_identifier():
    assert_identifier("APP", "ORDERS", "order_id")
    for bad in ["a;b", "x'y", "drop table", "1abc", ""]:
        with pytest.raises(ValueError):
            assert_identifier(bad)


# ---- H4/H5: engine.yaml context_material must reach the prompt -----------

def test_context_material_checks_injected_sqlserver_pg():
    # checks/non-portable-constructs.md is listed under context_material for this
    # pair; it must actually appear in the built context (previously dead).
    ctx = pb.build_context(pair="sqlserver-to-postgresql")
    assert "non-portable-constructs" in ctx.lower()
    assert "field-tested checklist" in ctx


def test_context_material_checks_injected_oracle_pg():
    # oracle-to-postgresql now ships checks/non-portable-constructs.md wired into
    # engine.yaml context_material, so it must reach the prompt.
    ctx = pb.build_context(pair="oracle-to-postgresql")
    assert "non-portable-constructs" in ctx.lower()
    assert "field-tested checklist" in ctx


def test_load_context_material_skips_already_injected(tmp_path):
    # A context_material list of only the construction skill / datatype map /
    # playbook dir yields no extra block (those are injected structurally).
    import textwrap
    (tmp_path / "engines" / "x-to-y").mkdir(parents=True)
    (tmp_path / "engines" / "x-to-y" / "engine.yaml").write_text(textwrap.dedent("""
        conversion:
          context_material:
            - skills/db-migration-construction/SKILL.md
            - engines/x-to-y/datatype-map.yaml
            - skills/x-to-y-playbook/references/
    """))
    assert pb._load_context_material(tmp_path, "x-to-y") == ""


# ---- token budget: phase-aware + shared context -----------------------------

def test_phase_contexts_are_scoped():
    schema = pb.build_context(pair="oracle-to-postgresql", phase=pb.SCHEMA)
    code = pb.build_context(pair="oracle-to-postgresql", phase=pb.CODE)
    tests = pb.build_context(pair="oracle-to-postgresql", phase=pb.TESTS)
    for ctx in (schema, code, tests):
        assert "# Construction skill guidance" not in ctx   # assistant already has it
        assert "High Availability" not in ctx               # never needed to convert
    assert "datatype reference" in schema and "datatype reference" in code
    assert "datatype reference" not in tests
    assert "spec format" in tests and "equivalence-spec" in tests
    assert len(tests) < len(code)


def test_shared_context_is_referenced_not_inlined(tmp_path):
    rel = pb.write_shared_context(tmp_path / "02-construction", pb.CODE,
                                  pair="oracle-to-postgresql")
    assert rel == "02-construction/_context-code.md"
    body = (tmp_path / rel).read_text()
    assert "datatype reference" in body
    from dbmig.engines.base import CodeObject
    obj = CodeObject("DEMO", "FUNCTION", "F", "CREATE FUNCTION f RETURN NUMBER IS BEGIN RETURN 1; END;")
    p = pb.build_code_prompt(obj, pair="oracle-to-postgresql", shared_context=rel)
    assert "migrations/<project>/02-construction/_context-code.md" in p
    assert "datatype reference" not in p
    assert len(p) < 3000


def test_construct_hints():
    src = "FUNCTION f RETURN t PIPELINED IS BEGIN SELECT NVL(a,0) INTO x FROM t WHERE ROWNUM<2; END; -- CONNECT BY"
    hints = pb.detect_constructs(src, "oracle-to-postgresql")
    assert any("PIPELINED" in h for h in hints)
    assert any("ROWNUM" in h for h in hints)
    assert not any("hierarchical" in h for h in hints)       # only in a comment
    assert any("APPLY" in h for h in pb.detect_constructs(
        "SELECT * FROM a CROSS APPLY f(a.id)", "sqlserver-to-postgresql"))


def test_test_prompt_uses_target_code_and_type_specific_format():
    p = pb.build_test_prompt("FUNCTION", "DEMO", "F", "CREATE FUNCTION f ...", {},
                             pair="oracle-to-postgresql",
                             target_code="CREATE FUNCTION demo.f() RETURNS int")
    assert "CREATE FUNCTION demo.f() RETURNS int" in p
    assert "**function**-shape spec" in p
    assert p.count("For a PROCEDURE") == 1        # format appears once (context), not twice
    p2 = pb.build_test_prompt("PROCEDURE", "DEMO", "P", "x", {}, pair="oracle-to-postgresql",
                              shared_context="03-validation/_context-tests.md")
    assert "**procedure**-shape spec" in p2 and "For a FUNCTION" not in p2   # shared: not inlined


def test_package_spec_and_body_merged():
    from dbmig.commands.convert_code import merge_spec_and_body
    from dbmig.engines.base import CodeObject as C
    objs = [C("S", "PACKAGE", "P", "CREATE PACKAGE P AS ... END; CREATE PACKAGE BODY P AS ... END;"),
            C("S", "FUNCTION", "F", "CREATE FUNCTION F ..."),
            C("S", "PACKAGE BODY", "P", "CREATE PACKAGE BODY P AS ... END;"),
            C("S", "PACKAGE", "Q", "CREATE PACKAGE Q AS END;")]      # spec-only package
    out, merged = merge_spec_and_body(objs)
    assert [(o.object_type, o.name) for o in out] == [("FUNCTION", "F"), ("PACKAGE", "P"), ("PACKAGE", "Q")]
    assert "PACKAGE BODY" in out[1].source_ddl and merged == {"PACKAGE": {"P"}}


# ---- playbook utilization: baseline, quick tips, target-aware hints ------------

_PAIRS = ("oracle-to-postgresql", "sqlserver-to-postgresql",
          "oracle-to-mysql", "sqlserver-to-mysql")


@pytest.mark.parametrize("pair", _PAIRS)
def test_target_baseline_and_quick_tips_injected(pair):
    for phase in (pb.SCHEMA, pb.CODE):
        ctx = pb.build_context(pair=pair, phase=phase)
        assert "# Target-version baseline" in ctx
        assert "## Conversion defaults" in ctx            # a real baseline section
        assert "## Which target version" not in ctx       # unselected sections stay out
        assert f"skills/{pair}-playbook/references/quick-tips/quick-tips.md" in ctx
    tests = pb.build_context(pair=pair, phase=pb.TESTS)
    assert "## Behavior differences" in tests and "## Conversion defaults" not in tests


@pytest.mark.parametrize("pair", _PAIRS)
def test_shared_context_size_budget(pair):
    # Written once per run, but still read by the assistant: keep it bounded.
    for phase in (pb.SCHEMA, pb.CODE, pb.TESTS):
        assert len(pb.build_context(pair=pair, phase=phase)) < 60_000


def test_chapter_without_index_is_listed():
    # deprecated-features/ has no _index.md; it used to be dropped silently.
    ctx = pb.build_context(pair="sqlserver-to-mysql", phase=pb.SCHEMA)
    assert "# deprecated-features/" in ctx and "deprecated-features.md" in ctx


def test_construct_hint_topic_files_exist():
    from dbmig import config
    root = config.find_repo_root()
    for source, entries in pb._CONSTRUCT_HINTS.items():
        for _pat, hints, topics in entries:
            assert set(topics) <= set(hints)
            for target, rel in topics.items():
                path = root / f"skills/{source}-to-{target}-playbook/references/{rel}"
                assert path.is_file(), path


def test_mysql_hints_are_not_postgresql():
    src = ("MERGE INTO t USING s ON (1=1) WHEN MATCHED THEN UPDATE SET a=1; "
           "EXECUTE IMMEDIATE v; x := s.NEXTVAL; SELECT TOP 5 * FROM #tmp "
           "CROSS APPLY f(x); SET @x = 'a' + @y; EXEC sp_executesql @s")
    for pair in ("oracle-to-mysql", "sqlserver-to-mysql"):
        hints = pb.detect_constructs(src, pair)
        assert hints
        joined = " ".join(hints)
        for pg_only in ("ON CONFLICT", "'||'", "EXECUTE format", "nextval", "PG15",
                        "CREATE TEMP TABLE"):
            assert pg_only not in joined, (pair, pg_only)
    my = pb.detect_constructs("MERGE INTO t USING s ON (1=1)", "oracle-to-mysql")
    assert "ON DUPLICATE KEY UPDATE" in my[0]
    assert "skills/oracle-to-mysql-playbook/references/sql-plsql/merge-statement.md" in my[0]


def test_code_instruction_names_target_language():
    assert "PL/pgSQL" not in pb._instruction("SQL Server", "mysql", code=True)
    assert "DECLARE … HANDLER" in pb._instruction("SQL Server", "mysql", code=True)
    assert "PL/pgSQL" in pb._instruction("Oracle", "postgresql", code=True)


def test_markdown_sections_selects_by_heading_prefix():
    text = "# T\n\nintro\n\n## Alpha one\na\n\n## Beta\nb\n\n## Alpha two\nc\n"
    out = pb._markdown_sections(text, ["alpha"])
    assert "## Alpha one" in out and "## Alpha two" in out and "Beta" not in out


def test_status_counts_playbook_citations(tmp_path):
    from dbmig.commands.status import playbook_citations
    log = tmp_path / "conversion-log.md"
    log.write_text("- ORDERS: MERGE per skills/oracle-to-mysql-playbook/references/sql-plsql/"
                   "merge-statement.md\n- X: see oracle-to-mysql-playbook/references/sql-plsql/"
                   "merge-statement.md and sqlserver-to-mysql-playbook/references/tsql/merge.md\n")
    c = playbook_citations(log)
    assert c["oracle-to-mysql-playbook/references/sql-plsql/merge-statement.md"] == 2
    assert len(c) == 2
    assert playbook_citations(tmp_path / "missing.md") == {}


def test_baseline_version_caution():
    from dbmig import config
    root = config.find_repo_root()
    on17 = pb._load_target_baseline(root, "oracle-to-postgresql", pb.CODE, target_version="17.7")
    on18 = pb._load_target_baseline(root, "oracle-to-postgresql", pb.CODE, target_version="18.6")
    assert "CAUTION — target version 17.7" in on17 and "CAUTION" not in on18
    assert "Target version not declared" in pb._load_target_baseline(
        root, "oracle-to-postgresql", pb.CODE, target_version="")
    # Aurora MySQL 3.x is MySQL 8.0, which the MySQL baseline covers.
    for v in ("3.13.0", "8.0", "8.4.8"):
        assert "CAUTION" not in pb._load_target_baseline(root, "oracle-to-mysql", pb.CODE,
                                                         target_version=v)
    assert "CAUTION" in pb._load_target_baseline(root, "sqlserver-to-mysql", pb.TESTS,
                                                 target_version="5.7")


def test_version_key():
    assert pb._version_key("postgresql", "17.7") == "17"
    assert pb._version_key("mysql", "8.4.mysql_aurora.8.4.8") == "8.4"
    assert pb._version_key("mysql", "3.13.0") == "8.0"
    assert pb._version_key("mysql", "") == ""


def test_resultset_compare():
    from dbmig.commands.run_tests import _resultset_equal
    s = [(1, "a", 2.5), (2, "b", None)]
    assert _resultset_equal(s, [(2, "b", None), (1, "a", 2.5000000001)], 1e-6, ordered=False)
    assert not _resultset_equal(s, [(2, "b", None), (1, "a", 2.5)], 1e-9, ordered=True)
    assert not _resultset_equal(s, s[:1], 1e-9, ordered=False)          # row count differs
    assert not _resultset_equal(s, [(1, "a", 2.5), (2, "c", None)], 1e-9, ordered=False)
    assert _resultset_equal([], [], 0.0, ordered=False)


@pytest.mark.parametrize("pair", _PAIRS)
def test_target_baseline_file_and_topic_links_exist(pair):
    import re
    from dbmig import config
    root = config.find_repo_root()
    cfg = (pb._engine_yaml(root, pair).get("conversion") or {}).get("target_baseline") or {}
    path = root / cfg["file"]
    assert path.is_file(), path
    refs = path.parent
    for rel in sorted(set(re.findall(r"`((?:[a-z-]+/)+[a-z0-9-]+\.md)`", path.read_text()))):
        if rel.startswith(("../", "customer-specific/")):   # per-engagement files
            continue
        assert (refs / rel).is_file(), f"{path.name}: {rel}"


def test_sqlserver_pg_baseline_is_sqlserver_specific():
    ctx = pb.build_context(pair="sqlserver-to-postgresql", phase=pb.CODE)
    assert "SQL Server construct" in ctx and "Oracle construct" not in ctx
