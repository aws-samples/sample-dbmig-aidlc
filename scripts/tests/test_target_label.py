import dbmig.commands.convert_schema as cs


def test_target_label_mysql(monkeypatch):
    monkeypatch.setattr(cs.config, "active_pair", lambda: "oracle-to-mysql")
    assert cs._target_label() == "MySQL"


def test_target_label_postgresql(monkeypatch):
    monkeypatch.setattr(cs.config, "active_pair", lambda: "sqlserver-to-postgresql")
    assert cs._target_label() == "PostgreSQL"


def test_target_label_falls_back_on_error(monkeypatch):
    def boom():
        raise RuntimeError("no connections file")
    monkeypatch.setattr(cs.config, "active_pair", boom)
    assert cs._target_label() == "PostgreSQL"
