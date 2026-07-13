import pytest

from dbmig import engines
from dbmig.config import ConfigError
from dbmig.connections import Connection
from dbmig.engines.base import SourceEngine, TargetEngine


def _pair(src, tgt):
    return {"source": Connection(engine=src), "target": Connection(engine=tgt)}


def test_get_source_and_target():
    p = _pair("oracle", "postgresql")
    assert isinstance(engines.get_source_engine(p), SourceEngine)
    assert isinstance(engines.get_target_engine(p), TargetEngine)


def test_aliases_resolve():
    p = _pair("mssql", "aurora-mysql")
    assert type(engines.get_source_engine(p)).__name__ == "SQLServerEngine"
    assert type(engines.get_target_engine(p)).__name__ == "MySQLEngine"


def test_role_guard_rejects_target_as_source():
    with pytest.raises(ConfigError):
        engines.get_source_engine(_pair("postgresql", "postgresql"))


def test_unknown_engine_rejected():
    with pytest.raises(ConfigError):
        engines.get_source_engine(_pair("db2", "postgresql"))
