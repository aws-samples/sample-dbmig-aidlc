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
