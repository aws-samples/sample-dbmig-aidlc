"""Legacy source compatibility: SQL Server 2008+ and Oracle 11.2+.

Modern sources (SQL Server 2017+, Oracle 12c+, or an undetectable version) must
keep the original query text; only an older detected/declared version switches
to the legacy form.
"""
import pytest

from dbmig import config
from dbmig.connections import Connection, _oracle_driver_mode
from dbmig.conversion import prompt_builder
from dbmig.engines.oracle import OracleEngine, build_sample_rows_sql
from dbmig.engines.sqlserver import SQLServerEngine


class _CaptureSQLServer(SQLServerEngine):
    """SQL Server engine that records SQL instead of executing it."""

    def __init__(self, version=None, detected="16.0.4135.4"):
        super().__init__(Connection(engine="sqlserver", host="h", version=version))
        self.sql = []
        self._detected = detected

    def scalar(self, sql, params=None):
        if "ProductVersion" in sql:
            if isinstance(self._detected, Exception):
                raise self._detected
            return self._detected
        self.sql.append(sql)
        return None

    def fetch(self, sql, params=None):
        self.sql.append(sql)
        return [], []


def _extract(eng):
    eng._constraints_ddl("Person", "Address")
    eng._foreign_keys_ddl("Person", "Address")
    eng._indexes_ddl("Person", "Address")
    return [s for s in eng.sql if "STRING_AGG" in s or "FOR XML PATH" in s]


@pytest.mark.parametrize("detected", ["14.0.3456.2", "15.0.4000.1", "16.0.4135.4"])
def test_sqlserver_2017_plus_keeps_string_agg(detected):
    sqls = _extract(_CaptureSQLServer(detected=detected))
    assert len(sqls) == 3
    assert all("STRING_AGG" in s and "FOR XML" not in s for s in sqls)


@pytest.mark.parametrize("detected", ["10.0.6000.29", "10.50.6000.34", "11.0.7001.0",
                                      "13.0.6300.2"])
def test_sqlserver_pre_2017_uses_for_xml_path(detected):
    sqls = _extract(_CaptureSQLServer(detected=detected))
    assert len(sqls) == 3
    assert all("FOR XML PATH('')" in s and "STRING_AGG" not in s for s in sqls)
    # ordered lists, separator stripped
    assert all("ORDER BY" in s and ", 1, 2, '')" in s for s in sqls)


def test_sqlserver_undetectable_version_stays_modern():
    eng = _CaptureSQLServer(detected=RuntimeError("no permission"))
    assert eng.major_version() is None
    assert all("STRING_AGG" in s for s in _extract(eng))


@pytest.mark.parametrize("declared,major", [("2008", 10), ("2008 R2", 10), ("10.50", 10),
                                            ("2016", 13), ("2022", 16), ("16", 16)])
def test_sqlserver_declared_version_overrides_detection(declared, major):
    eng = _CaptureSQLServer(version=declared, detected="16.0.1.0")
    assert eng.major_version() == major


def test_sqlserver_legacy_note_only_for_old_versions():
    assert _CaptureSQLServer(detected="16.0.1.0").legacy_syntax_note() == ""
    note = _CaptureSQLServer(detected="10.50.6000.34").legacy_syntax_note()
    assert "major version 10" in note and "STRING_AGG" in note and "IIF" in note
    note13 = _CaptureSQLServer(detected="13.0.1.0").legacy_syntax_note()
    assert "STRING_AGG" in note13 and "IIF" not in note13


class _FakeOracleConn:
    def __init__(self, version):
        self.version = version


def _oracle(version=None, detected="19.0.0.0.0"):
    eng = OracleEngine(Connection(engine="oracle", host="h", service_name="s",
                                  version=version))
    eng._conn = _FakeOracleConn(detected)
    return eng


def test_oracle_version_detection_and_override():
    assert _oracle(detected="11.2.0.2.0").major_version() == 11
    assert _oracle(detected="19.0.0.0.0").major_version() == 19
    assert _oracle(version="11g", detected="19.0.0.0.0").major_version() == 11


def test_oracle_sample_sql_by_version():
    assert build_sample_rows_sql("DEMO", "T", 3) == \
        "SELECT * FROM DEMO.T FETCH FIRST 3 ROWS ONLY"
    assert build_sample_rows_sql("DEMO", "T", 3, legacy=True) == \
        "SELECT * FROM DEMO.T WHERE ROWNUM <= 3"
    assert _oracle(detected="11.2.0.2.0")._legacy() is True
    assert _oracle(detected="12.1.0.2.0")._legacy() is False
    assert _oracle(detected=None)._legacy() is False   # unknown => modern


def test_oracle_legacy_note():
    assert _oracle(detected="19.0.0.0.0").legacy_syntax_note() == ""
    assert "FETCH FIRST" in _oracle(detected="11.2.0.4.0").legacy_syntax_note()


def test_oracle_driver_mode(monkeypatch):
    monkeypatch.delenv("DBMIG_ORACLE_DRIVER_MODE", raising=False)
    assert _oracle_driver_mode(Connection(engine="oracle")) == "thin"
    assert _oracle_driver_mode(Connection(engine="oracle",
                                          extra={"driver_mode": "Thick"})) == "thick"
    with pytest.raises(config.ConfigError):
        _oracle_driver_mode(Connection(engine="oracle", extra={"driver_mode": "x"}))


def test_test_prompt_unchanged_without_note(tmp_path):
    objs = [{"obj_type": "FUNCTION", "name": "F", "source_ddl": "x", "target_code": None}]
    base = prompt_builder.build_test_batch_prompt(objs, "S", {}, repo_root=tmp_path,
                                                  pair="sqlserver-to-postgresql",
                                                  shared_context="ctx.md")
    same = prompt_builder.build_test_batch_prompt(objs, "S", {}, repo_root=tmp_path,
                                                  pair="sqlserver-to-postgresql",
                                                  shared_context="ctx.md", source_note="")
    noted = prompt_builder.build_test_batch_prompt(objs, "S", {}, repo_root=tmp_path,
                                                   pair="sqlserver-to-postgresql",
                                                   shared_context="ctx.md",
                                                   source_note="SOURCE VERSION: X")
    assert base == same
    assert "SOURCE VERSION: X" in noted and "SOURCE VERSION" not in base
