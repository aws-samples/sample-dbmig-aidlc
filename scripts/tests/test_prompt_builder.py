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
