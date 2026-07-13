"""Configuration loading: connections.yaml + migration-config.yaml.

- Expands ``${ENV_VAR}`` references from the environment.
- ``CONN_FILE`` env var overrides the connections path (default ``./connections.yaml``).
- ``MIGRATION_CONFIG`` env var overrides the migration-config path
  (default ``./migration-config.yaml``).
- Locates the repository root (the directory containing ``skills/`` and ``engines/``)
  so skill/playbook context can be injected into conversion prompts.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

_ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ConfigError(Exception):
    pass


def expand_env(value: Any) -> Any:
    """Recursively expand ${VAR} references in strings within a structure.

    Warns (once, listing the names) when a referenced variable is unset — an unset
    ``${DB_PASSWORD}`` would otherwise silently become an empty string (e.g. a blank
    password), which is hard to diagnose."""
    missing: list = []

    def _exp(v: Any) -> Any:
        if isinstance(v, str):
            def _repl(m):
                name = m.group(1)
                if name not in os.environ and name not in missing:
                    missing.append(name)
                return os.environ.get(name, "")
            return _ENV_RE.sub(_repl, v)
        if isinstance(v, dict):
            return {k: _exp(x) for k, x in v.items()}
        if isinstance(v, list):
            return [_exp(x) for x in v]
        return v

    out = _exp(value)
    if missing:
        try:
            from . import console
            console.warn("unset environment variable(s) referenced in config, using "
                         "empty string: " + ", ".join("${%s}" % n for n in missing))
        except Exception:
            pass
    return out


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"file not found: {path}")
    with path.open() as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"expected a YAML mapping at top level of {path}")
    return expand_env(data)


def connections_path() -> Path:
    return Path(os.environ.get("CONN_FILE", "connections.yaml")).expanduser()


def migration_config_path() -> Path:
    return Path(os.environ.get("MIGRATION_CONFIG", "migration-config.yaml")).expanduser()


def load_connections() -> Dict[str, Any]:
    return _load_yaml(connections_path())


def load_migration_config(required: bool = False) -> Dict[str, Any]:
    path = migration_config_path()
    if not path.exists():
        if required:
            raise ConfigError(f"migration config not found: {path}")
        return {}
    return _load_yaml(path)


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Walk upward from ``start`` (and this module) to find the repo root.

    The repo root is the first ancestor that contains both ``skills/`` and
    ``engines/`` directories. Falls back to the current working directory.
    """
    candidates = []
    if start:
        candidates.append(Path(start).resolve())
    candidates.append(Path.cwd().resolve())
    candidates.append(Path(__file__).resolve())

    for base in candidates:
        for d in [base, *base.parents]:
            if (d / "skills").is_dir() and (d / "engines").is_dir():
                return d
    # Sentinels not found anywhere upward — conversions read repo files (skills,
    # engines, playbook) relative to this root, so a wrong root silently yields an
    # empty knowledge base. Warn loudly rather than fail (some standalone steps work).
    try:
        from . import console
        console.warn("could not locate the repo root (no directory with both "
                     "skills/ and engines/ found upward); falling back to the current "
                     "directory — conversion context may be incomplete.")
    except Exception:
        pass
    return Path.cwd().resolve()


# ---- LLM config -----------------------------------------------------------

DEFAULT_LLM = {
    # The LLM is Kiro itself. The package prepares prompt bundles and hands them
    # to the Kiro db-migration-construction skill for conversion; it makes no API
    # calls. "provider: kiro" selects this hand-off behavior.
    "provider": "kiro",
    "model": "kiro",
    "max_tokens": 4096,
    # Error-retry loop: max apply attempts per unit before a unit is marked
    # needs_human. On a failed apply, the PostgreSQL error is fed back to Kiro
    # (via a remediation prompt) and the unit is re-converted and re-applied,
    # up to this many attempts. Minimizes human-in-the-loop.
    "max_retries": 3,
    # Tables with <= this many rows are eligible to be batched into a shared
    # prompt to reduce conversion round-trips.
    "batch_row_threshold": 100000,
    # Maximum object-units grouped into a single batch prompt.
    "batch_max_units": 5,
}


def llm_config(mig_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = dict(DEFAULT_LLM)
    if mig_cfg is None:
        mig_cfg = load_migration_config()
    user_llm = mig_cfg.get("llm") or {}
    if isinstance(user_llm, dict):
        cfg.update({k: v for k, v in user_llm.items() if v is not None})
    return cfg


def migrations_root() -> Path:
    """Root directory that holds per-project run workspaces.

    Defaults to ``<repo>/migrations`` but can be redirected anywhere with the
    ``DBMIG_MIGRATIONS_DIR`` env var — point it outside the repo for fully
    isolated test runs that can be deleted without touching the project folder.
    """
    override = os.environ.get("DBMIG_MIGRATIONS_DIR")
    if override:
        return Path(override).expanduser()
    return find_repo_root() / "migrations"


def workspace_dir(project: str) -> Path:
    """Per-project run workspace (created on demand by callers). Honors
    DBMIG_MIGRATIONS_DIR for out-of-repo, easily-cleaned-up test runs."""
    return migrations_root() / project


_PROJECT_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_project(name: Optional[str]) -> str:
    """Normalize an arbitrary project label into a safe single-segment folder name.

    Rather than rejecting odd input, it repairs it: drops quotes/apostrophes, turns
    whitespace into dashes, replaces any other filesystem-unsafe character with a
    dash, collapses repeats, and trims leading/trailing separators. Path separators
    become dashes and leading dots are trimmed, so the result is always a single,
    traversal-safe segment. Falls back to ``default`` if nothing usable remains.
    Example: ``"my's test run"`` -> ``"mys-test-run"``.
    """
    s = (name or "").strip()
    for q in ("'", '"', "`"):
        s = s.replace(q, "")               # omit quotes/apostrophes
    s = re.sub(r"\s+", "-", s)              # whitespace -> dash
    s = _PROJECT_UNSAFE_RE.sub("-", s)      # any other unsafe char -> dash
    s = re.sub(r"-{2,}", "-", s).strip("-._")
    if not s or set(s) <= {"."}:            # empty or all-dots -> not usable
        return "default"
    return s


def resolve_project(cli_value: Optional[str]) -> str:
    """Effective project name: the CLI ``--project`` if given, else the
    ``project:`` key in migration-config.yaml, else ``default`` — then sanitized to
    a safe folder name via :func:`sanitize_project`."""
    raw = (cli_value or "").strip()
    if not raw:
        try:
            raw = str((load_migration_config().get("project") or "")).strip()
        except Exception:
            raw = ""
    return sanitize_project(raw or "default")


def manifest_file(base: str, schema: Optional[str]) -> str:
    """Manifest filename, scoped by schema so one project can hold multiple
    schemas. ``base`` is ``manifest`` / ``code-manifest`` / ``test-manifest``."""
    if schema:
        return f"{base}-{schema.upper()}.yaml"
    return f"{base}.yaml"


def resolve_manifest(ws: Path, base: str, schema: Optional[str],
                     *, for_write: bool = False) -> Path:
    """Resolve a (schema-scoped) manifest path under workspace ``ws``.

    Writes always use the schema-scoped name (``manifest-<SCHEMA>.yaml``) so two
    schemas in the same project don't overwrite each other. Reads prefer the
    scoped name but fall back to the legacy unscoped ``manifest.yaml`` if only
    that exists — keeping older single-schema runs working.
    """
    scoped = ws / manifest_file(base, schema)
    legacy = ws / f"{base}.yaml"
    if for_write or not schema:
        return scoped if schema else legacy
    if scoped.exists():
        return scoped
    return legacy if legacy.exists() else scoped


# ---- engine pair resolution ----------------------------------------------

def normalize_engine(engine: Optional[str]) -> str:
    e = (engine or "").strip().lower()
    if e in ("postgres", "aurora-postgresql"):
        return "postgresql"
    if e in ("aurora-mysql", "mariadb"):
        return "mysql"
    if e in ("mssql", "sql-server", "sql_server", "sql server"):
        return "sqlserver"
    return e or ""


def active_pair() -> str:
    """Return the active engine pair id, e.g. 'oracle-to-postgresql' or
    'oracle-to-mysql', derived from the connections file. Falls back to
    oracle-to-postgresql if connections can't be read."""
    try:
        raw = load_connections()
    except Exception:
        return "oracle-to-postgresql"
    src = normalize_engine((raw.get("source") or {}).get("engine")) or "oracle"
    tgt = normalize_engine((raw.get("target") or {}).get("engine")) or "postgresql"
    return f"{src}-to-{tgt}"
