"""Unit tests for the FDW push-down data-load path (``migrate-data --method fdw``).

Pure-function coverage — no database needed:
  * PostgreSQL FDW SQL builders (extension/server/user-mapping/foreign-table/
    insert-select/delete-range), option-value escaping, and identifier validation.
  * Source engine FDW descriptors (oracle_fdw / tds_fdw) and the tds_fdw temporal
    column-declaration template.
  * The target-capability guard (PostgreSQL fdw_capable, MySQL not).
"""
import pytest

from dbmig.connections import Connection
from dbmig.engines import postgresql as pg
from dbmig.engines.postgresql import PostgreSQLEngine
from dbmig.engines.mysql import MySQLEngine
from dbmig.engines.oracle import OracleEngine
from dbmig.engines.sqlserver import SQLServerEngine


# ---- target capability guard ----------------------------------------------

def test_fdw_capability_flag():
    assert PostgreSQLEngine.fdw_capable is True
    assert MySQLEngine.fdw_capable is False


# ---- PostgreSQL builders ---------------------------------------------------

def test_create_extension_sql_validates_name():
    assert pg.build_create_extension_sql("oracle_fdw") == \
        "CREATE EXTENSION IF NOT EXISTS oracle_fdw"
    with pytest.raises(ValueError):
        pg.build_create_extension_sql("evil; DROP TABLE x")


def test_option_value_escaping_doubles_quotes():
    # A password/option value with a single quote must be escaped, not break out.
    sql = pg.build_create_user_mapping_sql("dbmig_fdw_srv",
                                           {"user": "admin", "password": "a'b"})
    assert "OPTIONS (user 'admin', password 'a''b')" in sql
    assert sql.startswith("CREATE USER MAPPING FOR CURRENT_USER SERVER \"dbmig_fdw_srv\"")


def test_option_key_validated():
    with pytest.raises(ValueError):
        pg.build_create_server_sql("s", "oracle_fdw", {"bad key": "v"})


def test_create_foreign_table_sql():
    sql = pg.build_create_foreign_table_sql(
        "dbmig_fdw_demo", "employees",
        [("EMP_ID", "bigint"), ("NAME", "character varying(50)")],
        "dbmig_fdw_srv", {"schema": "DEMO", "table": "EMPLOYEES"})
    assert '"dbmig_fdw_demo"."employees"' in sql
    assert '"EMP_ID" bigint' in sql
    assert '"NAME" character varying(50)' in sql
    assert "SERVER \"dbmig_fdw_srv\" OPTIONS (schema 'DEMO', table 'EMPLOYEES')" in sql


def test_insert_select_whole_table():
    sql = pg.build_fdw_insert_select_sql(
        "demo", "employees", ["emp_id", "name"],
        "dbmig_fdw_demo", "employees", ['"EMP_ID"', '"NAME"'])
    assert sql == ('INSERT INTO "demo"."employees" ("emp_id", "name") '
                   'SELECT "EMP_ID", "NAME" FROM "dbmig_fdw_demo"."employees"')


def test_insert_select_shard_range_inlined():
    sql = pg.build_fdw_insert_select_sql(
        "demo", "employees", ["emp_id", "name"],
        "dbmig_fdw_demo", "employees", ['"EMP_ID"', '"NAME"'],
        pk="EMP_ID", lo=0, hi=1000)
    assert sql.endswith('WHERE "EMP_ID" >= 0 AND "EMP_ID" < 1000')


def test_insert_select_accepts_cast_expression():
    # A tds_fdw-style normalization expression is emitted verbatim in the SELECT.
    expr = "CAST(regexp_replace(\"BirthDate\", 'x', 'y') AS date)"
    sql = pg.build_fdw_insert_select_sql(
        "hr", "employee", ["birthdate"], "dbmig_fdw_hr", "employee", [expr])
    assert f"SELECT {expr} FROM" in sql


def test_delete_range_sql_inlines_ints():
    sql = pg.build_fdw_delete_range_sql("demo", "employees", "emp_id", 5, 9)
    assert sql == ('DELETE FROM "demo"."employees" '
                   'WHERE "emp_id" >= 5 AND "emp_id" < 9')


# ---- Oracle (oracle_fdw) descriptor ---------------------------------------

def _ora(**kw):
    base = dict(engine="oracle", host="h", port=1521, username="u", password="p")
    base.update(kw)
    return OracleEngine(Connection(**base))


def test_oracle_fdw_descriptor_service_name_ezconnect():
    o = _ora(service_name="ORCLPDB1")
    assert o.fdw_wrapper() == "oracle_fdw"
    assert o.fdw_server_options() == {"dbserver": "//h:1521/ORCLPDB1"}
    assert o.fdw_user_mapping_options() == {"user": "u", "password": "p"}
    assert o.fdw_foreign_table_options("demo", "emp") == {"schema": "DEMO", "table": "EMP"}


def test_oracle_fdw_descriptor_sid_uses_descriptor():
    o = _ora(sid="ORCL")
    dbserver = o.fdw_server_options()["dbserver"]
    assert dbserver.startswith("(DESCRIPTION=")
    assert "(SID=ORCL)" in dbserver


def test_oracle_fdw_column_decl_is_identity():
    o = _ora(sid="ORCL")
    assert o.fdw_column_decl("numeric(10,2)") == ("numeric(10,2)", None)


# ---- SQL Server (tds_fdw) descriptor --------------------------------------

def _mss(**kw):
    base = dict(engine="sqlserver", host="h", port=1433, username="u", password="p",
                database="AdventureWorks")
    base.update(kw)
    return SQLServerEngine(Connection(**base))


def test_sqlserver_fdw_descriptor():
    s = _mss()
    assert s.fdw_wrapper() == "tds_fdw"
    opts = s.fdw_server_options()
    assert opts["servername"] == "h" and opts["port"] == "1433"
    assert opts["database"] == "AdventureWorks" and opts["msg_handler"] == "blackhole"
    # tds_fdw uses 'username', NOT 'user'.
    assert s.fdw_user_mapping_options() == {"username": "u", "password": "p"}
    ft = s.fdw_foreign_table_options("Person", "Person")
    assert ft["schema_name"] == "Person" and ft["table_name"] == "Person"
    assert ft["match_column_names"] == "1"


def test_sqlserver_fdw_column_decl_non_temporal_is_identity():
    s = _mss()
    assert s.fdw_column_decl("integer") == ("integer", None)
    assert s.fdw_column_decl("character varying(50)") == ("character varying(50)", None)


def test_sqlserver_fdw_column_decl_temporal_declares_text_with_cast():
    s = _mss()
    for tt in ("date", "timestamp without time zone", "time without time zone"):
        decl, tmpl = s.fdw_column_decl(tt)
        assert decl == "text"
        assert tmpl is not None and "{col}" in tmpl
        assert f"AS {tt})" in tmpl
        # Renders a valid, target-castable expression when a column is substituted.
        expr = tmpl.format(col='"BirthDate"')
        assert expr.startswith("CAST(regexp_replace(")
        assert '"BirthDate"' in expr
