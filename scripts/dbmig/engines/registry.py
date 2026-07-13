"""Engine registry: maps engine names to adapter classes.

To add a new engine, implement SourceEngine and/or TargetEngine in a module and
register the class here. Nothing else (CLI, prompt builder, data migration,
reconciliation) needs to change.
"""
from __future__ import annotations

from typing import Dict, Type

from .. import config
from ..connections import Connection
from .base import Engine, SourceEngine, TargetEngine


def _load_engines() -> Dict[str, Type[Engine]]:
    # Imported lazily so the package imports without every DB driver installed.
    from .oracle import OracleEngine
    from .postgresql import PostgreSQLEngine
    from .mysql import MySQLEngine
    from .sqlserver import SQLServerEngine
    return {
        "oracle": OracleEngine,
        "postgresql": PostgreSQLEngine,
        "mysql": MySQLEngine,
        "sqlserver": SQLServerEngine,
    }


# Engine-name aliases are normalized in a single place: config.normalize_engine.
def _canonical(engine: str) -> str:
    return config.normalize_engine(engine)


def _make(model: Connection, role: str) -> Engine:
    key = _canonical(model.engine)
    engines = _load_engines()
    cls = engines.get(key)
    if cls is None:
        raise config.ConfigError(
            f"unsupported engine '{model.engine}'. Registered engines: "
            f"{', '.join(sorted(engines))}")
    inst = cls(model)
    if role == "source" and not isinstance(inst, SourceEngine):
        raise config.ConfigError(f"engine '{model.engine}' cannot be a migration source")
    if role == "target" and not isinstance(inst, TargetEngine):
        raise config.ConfigError(f"engine '{model.engine}' cannot be a migration target")
    return inst


def get_source_engine(pair: Dict[str, Connection]) -> SourceEngine:
    if "source" not in pair:
        raise config.ConfigError("no 'source' connection defined")
    return _make(pair["source"], "source")  # type: ignore[return-value]


def get_target_engine(pair: Dict[str, Connection]) -> TargetEngine:
    if "target" not in pair:
        raise config.ConfigError("no 'target' connection defined")
    return _make(pair["target"], "target")  # type: ignore[return-value]
