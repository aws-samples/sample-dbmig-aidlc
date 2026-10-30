import pytest

from dbmig import config
from dbmig.connections import (MYSQL_STRICT_SQL_MODE, Connection,
                               mysql_session_sql_mode)


def _c(**extra):
    return Connection.from_dict({"engine": "mysql", "host": "h", **extra})


def test_default_is_strict():
    # Aurora MySQL default parameter groups leave GLOBAL sql_mode empty; dbmig must not.
    assert mysql_session_sql_mode(_c()) == MYSQL_STRICT_SQL_MODE
    assert "STRICT_TRANS_TABLES" in MYSQL_STRICT_SQL_MODE


def test_server_and_explicit_modes():
    assert mysql_session_sql_mode(_c(sql_mode="server")) is None
    assert mysql_session_sql_mode(_c(sql_mode="strict_all_tables, pipes_as_concat")) == \
        "STRICT_ALL_TABLES,PIPES_AS_CONCAT"


def test_rejects_injection():
    with pytest.raises(config.ConfigError):
        mysql_session_sql_mode(_c(sql_mode="STRICT_TRANS_TABLES'; DROP DATABASE x; --"))
