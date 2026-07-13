import os

from dbmig import config


def test_expand_env(monkeypatch):
    monkeypatch.setenv("DBMIG_T_HOST", "h1")
    out = config.expand_env({"a": "${DBMIG_T_HOST}", "b": ["${DBMIG_T_HOST}", 5], "c": 7})
    assert out == {"a": "h1", "b": ["h1", 5], "c": 7}


def test_expand_env_missing_var_is_empty():
    assert config.expand_env("${DBMIG_DOES_NOT_EXIST_XYZ}") == ""


def test_normalize_engine():
    assert config.normalize_engine("aurora-postgresql") == "postgresql"
    assert config.normalize_engine("postgres") == "postgresql"
    assert config.normalize_engine("aurora-mysql") == "mysql"
    assert config.normalize_engine("mssql") == "sqlserver"
    assert config.normalize_engine("sql-server") == "sqlserver"
    assert config.normalize_engine("ORACLE") == "oracle"


def test_active_pair(tmp_path, monkeypatch):
    f = tmp_path / "connections.yaml"
    f.write_text("source:\n  engine: mssql\ntarget:\n  engine: aurora-mysql\n")
    monkeypatch.setenv("CONN_FILE", str(f))
    assert config.active_pair() == "sqlserver-to-mysql"


def test_active_pair_falls_back(monkeypatch):
    monkeypatch.setenv("CONN_FILE", "/nope/does-not-exist.yaml")
    assert config.active_pair() == "oracle-to-postgresql"


def test_migrations_dir_override(tmp_path, monkeypatch):
    monkeypatch.setenv("DBMIG_MIGRATIONS_DIR", str(tmp_path))
    ws = config.workspace_dir("proj1")
    assert ws == tmp_path / "proj1"


def test_migrations_dir_default_in_repo(monkeypatch):
    monkeypatch.delenv("DBMIG_MIGRATIONS_DIR", raising=False)
    ws = config.workspace_dir("proj1")
    assert ws.parent.name == "migrations"


# ---- project name sanitization + resolution ------------------------------

def test_sanitize_project_repairs_input():
    assert config.sanitize_project("my's test run") == "mys-test-run"
    assert config.sanitize_project("  spaced   name ") == "spaced-name"
    assert config.sanitize_project("adventureworks-20260703") == "adventureworks-20260703"
    assert config.sanitize_project("Keep_Case.1-2") == "Keep_Case.1-2"


def test_sanitize_project_fallback_and_traversal_safe():
    for bad in ("", None, "   ", "...", "''", "''' "):
        assert config.sanitize_project(bad) == "default"
    # path separators become dashes and leading dots are trimmed -> single safe segment
    for name in ("weird/../path", "..\\etc\\x", "/abs/path"):
        s = config.sanitize_project(name)
        assert "/" not in s and "\\" not in s
        assert not s.startswith(".")


def test_resolve_project_precedence(monkeypatch):
    # explicit CLI value wins (and is sanitized)
    assert config.resolve_project("Prod Run") == "Prod-Run"
    # no CLI value -> falls back to migration-config 'project:'
    monkeypatch.setattr(config, "load_migration_config", lambda *a, **k: {"project": "cfg run"})
    assert config.resolve_project(None) == "cfg-run"
    # no CLI value and no config -> 'default'
    monkeypatch.setattr(config, "load_migration_config", lambda *a, **k: {})
    assert config.resolve_project(None) == "default"
