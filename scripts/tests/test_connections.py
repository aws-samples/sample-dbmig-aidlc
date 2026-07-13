import pytest

from dbmig.config import ConfigError
from dbmig.connections import Connection


def test_from_dict_basic():
    c = Connection.from_dict({"engine": "oracle", "host": "h", "port": 1521,
                              "username": "u", "password": "secret",
                              "service_name": "ORCL"})
    assert c.engine == "oracle" and c.port == 1521 and c.service_name == "ORCL"


def test_from_dict_requires_engine():
    with pytest.raises(ConfigError):
        Connection.from_dict({"host": "h"})


def test_from_dict_bad_port():
    with pytest.raises(ConfigError):
        Connection.from_dict({"engine": "mysql", "port": "not-a-number"})


def test_password_is_masked():
    c = Connection.from_dict({"engine": "postgresql", "host": "h", "port": 5432,
                              "username": "u", "password": "topsecret",
                              "database": "db"})
    assert "topsecret" not in repr(c)
    assert "topsecret" not in c.safe()
    assert c.safe().startswith("postgresql://u@h:5432/")
