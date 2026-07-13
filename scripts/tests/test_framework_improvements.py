"""Tests for the six framework improvements learned from the real sample runs."""
from dbmig import config
from dbmig.engines import sqlserver
from dbmig.commands import gen_tests, migrate_data, mark
from dbmig.conversion.prompt_builder import _format_sample


# ---- Security: sampled-data redaction ------------------------------------

def test_format_sample_redacts_sensitive_columns():
    sample = {"customers": (
        ["id", "email", "password_hash", "PasswordSalt", "api_token", "role"],
        [(1, "a@example.com", "$2a$10$dXJ3SW6secrethash", "s4lt", "tok-123", "ADMIN")])}
    out = _format_sample(sample)
    # secrets/PII from sensitive-named columns are masked
    assert "$2a$10$dXJ3SW6secrethash" not in out
    assert "s4lt" not in out
    assert "tok-123" not in out
    assert "<redacted>" in out
    # non-sensitive values are preserved for grounding
    assert "a@example.com" in out
    assert "ADMIN" in out


def test_format_sample_keeps_ordinary_data():
    sample = {"genres": (["id", "name"], [(1, "History")])}
    out = _format_sample(sample)
    assert "History" in out and "<redacted>" not in out


def test_format_sample_does_not_over_redact_flag_columns():
    # Flag/metadata columns that merely contain a secret-ish word are NOT secrets:
    # they hold a boolean/timestamp and must be preserved for grounding, while the
    # real secret columns are still redacted.
    sample = {"customers": (
        ["id", "credentials_expired", "account_locked", "password_changed_at",
         "token_expiry", "password_hash", "api_key"],
        [(7, 0, 1, "2026-01-02 03:04:05", "2026-06-01 00:00:00",
          "$2a$10$abcdEF", "AKIA-xyz-123")])}
    out = _format_sample(sample)
    # boolean flags / timestamps preserved
    assert "| 0 |" in out                      # credentials_expired
    assert "2026-01-02 03:04:05" in out         # password_changed_at
    assert "2026-06-01 00:00:00" in out         # token_expiry
    # genuine secrets still masked
    assert "$2a$10$abcdEF" not in out
    assert "AKIA-xyz-123" not in out
    assert "<redacted>" in out


# ---- Item 1: SQL Server read-time conversion expressions -----------------

def test_read_expr_template():
    assert sqlserver.read_expr_template("hierarchyid") == "{col}.ToString()"
    assert sqlserver.read_expr_template("geography") == "{col}.STAsText()"
    assert sqlserver.read_expr_template("GEOMETRY") == "{col}.STAsText()"
    assert sqlserver.read_expr_template("int") is None
    assert sqlserver.read_expr_template(None) is None


# ---- Security: identifier-quoting SQL builders ---------------------------
# The builders keep interpolated identifiers OUT of the execute() call site
# (so static analyzers don't flag a formatted query at the sink) while quoting
# and validating identifiers. See SECURITY.md ("SQL construction").

def test_postgresql_sql_builders_quote_identifiers():
    from dbmig.engines import postgresql as pg
    assert pg.build_create_schema_sql("demo") == 'CREATE SCHEMA IF NOT EXISTS "demo"'
    assert pg.build_row_count_sql("demo", "orders") == 'SELECT COUNT(*) FROM "demo"."orders"'
    assert pg.build_truncate_sql("s", "t") == 'TRUNCATE TABLE "s"."t"'
    assert pg.build_copy_sql("s", "t", ["a", "b"]) == 'COPY "s"."t" ("a", "b") FROM STDIN'
    # embedded double-quote in an identifier is escaped, not injectable
    assert pg.build_row_count_sql("s", 'x"; DROP TABLE y --') == \
        'SELECT COUNT(*) FROM "s"."x""; DROP TABLE y --"'
    # setval keeps the sequence as a bound %s param
    assert pg.build_setval_max_sql("s", "t", "id") == \
        'SELECT setval(%s, COALESCE((SELECT MAX("id") FROM "s"."t"), 1))'


def test_mysql_sql_builders_quote_identifiers():
    from dbmig.engines import mysql as my
    assert my.build_create_database_sql("demo") == "CREATE DATABASE IF NOT EXISTS `demo`"
    assert my.build_row_count_sql("s", "t") == "SELECT COUNT(*) FROM `s`.`t`"
    assert my.build_insert_sql("s", "t", ["a", "b"]) == \
        "INSERT INTO `s`.`t` (`a`, `b`) VALUES (%s, %s)"
    assert my.build_set_auto_increment_sql("s", "t", 42) == \
        "ALTER TABLE `s`.`t` AUTO_INCREMENT = 42"
    # embedded backtick escaped
    assert my.build_row_count_sql("s", "a`b") == "SELECT COUNT(*) FROM `s`.`a``b`"


def test_oracle_sample_rows_builder_validates_identifiers():
    import pytest
    from dbmig.engines import oracle as ora
    assert ora.build_sample_rows_sql("DEMO", "ORDERS", 5) == \
        "SELECT * FROM DEMO.ORDERS FETCH FIRST 5 ROWS ONLY"
    # unsafe identifiers are rejected before interpolation
    with pytest.raises(ValueError):
        ora.build_sample_rows_sql("DEMO", "bad; DROP TABLE x", 5)



def test_select_list_applies_conversions_and_aliases():
    sql = sqlserver._select_list(
        [("id", "int"), ("node", "hierarchyid"), ("loc", "geography"), ("name", "nvarchar")])
    assert sql == "[id], [node].ToString() AS [node], [loc].STAsText() AS [loc], [name]"


def test_select_list_empty():
    assert sqlserver._select_list([]) == "*"


# ---- Item 2: schema-scoped inventory filename ----------------------------

def test_inventory_filename_is_schema_scoped():
    assert config.manifest_file("inventory", "Person") == "inventory-PERSON.yaml"
    assert config.manifest_file("inventory", None) == "inventory.yaml"


# ---- Item 3: transaction-managed procedure detection ---------------------

def test_self_manages_transaction_true():
    assert gen_tests.self_manages_transaction("BEGIN TRANSACTION\nUPDATE t SET x=1\nCOMMIT")
    assert gen_tests.self_manages_transaction("UPDATE t SET x=1;\nCOMMIT;")
    assert gen_tests.self_manages_transaction("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION")
    assert gen_tests.self_manages_transaction("SAVE TRAN sp1")


def test_self_manages_transaction_false():
    assert not gen_tests.self_manages_transaction("UPDATE t SET x=1 WHERE id=@p")
    assert not gen_tests.self_manages_transaction("")
    # a commented-out COMMIT must not trip detection
    assert not gen_tests.self_manages_transaction("UPDATE t SET x=1; -- COMMIT later")
    assert not gen_tests.self_manages_transaction("/* COMMIT */ UPDATE t SET x=1")


# ---- Item 4: migrate-data include/exclude selection ----------------------

def test_select_tables_include_and_exclude():
    names = ["Address", "Employee", "Department", "Shift"]
    # exclude only (case-insensitive)
    assert migrate_data._select_tables(names, None, ["employee"]) == \
        ["Address", "Department", "Shift"]
    # include only
    assert migrate_data._select_tables(names, ["Address", "Shift"], None) == \
        ["Address", "Shift"]
    # include then exclude (exclude wins on overlap)
    assert migrate_data._select_tables(names, ["Address", "Employee"], ["employee"]) == \
        ["Address"]
    # no filters -> unchanged
    assert migrate_data._select_tables(names, None, None) == names


def test_parse_list():
    assert migrate_data._parse_list("a, b ,c") == ["a", "b", "c"]
    assert migrate_data._parse_list(None) == []
    assert migrate_data._parse_list("") == []


# ---- Item 6: mark.apply_status -------------------------------------------

def _manifest():
    return {"units": [
        {"name": "A", "status": "pending", "output_file": "ddl/a.sql"},
        {"name": "B", "status": "pending", "output_file": "ddl/b.sql"},
        {"name": "C", "status": "applied", "output_file": "ddl/c.sql"},
    ]}


def test_apply_status_all():
    m = _manifest()
    n = mark.apply_status(m, "converted")
    assert n == 3  # A, B (pending) and C (applied) all differ from 'converted'
    assert [u["status"] for u in m["units"]] == ["converted", "converted", "converted"]


def test_apply_status_only_subset():
    m = _manifest()
    n = mark.apply_status(m, "converted", only=["a"])
    assert n == 1
    assert m["units"][0]["status"] == "converted"
    assert m["units"][1]["status"] == "pending"


def test_apply_status_require_output(tmp_path):
    m = _manifest()
    (tmp_path / "ddl").mkdir()
    (tmp_path / "ddl" / "a.sql").write_text("x")  # only A has an output file present
    n = mark.apply_status(m, "converted", ws=tmp_path, require_output=True)
    assert n == 1
    assert m["units"][0]["status"] == "converted"
    assert m["units"][1]["status"] == "pending"
