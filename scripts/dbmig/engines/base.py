"""Engine adapter base classes and engine-neutral data structures.

The dbmig commands depend ONLY on these interfaces (resolved via
``engines.registry``); they never import engine-specific modules directly. To add
a new engine, implement ``SourceEngine`` and/or ``TargetEngine`` in a new module
and register it in ``engines/registry.py``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import re
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

from . import _common

# ---- identifier safety -----------------------------------------------------

# Schema/table/column names that are interpolated into SQL (rather than bound as
# parameters) must match this conservative pattern. Accepts the characters real
# Oracle/SQL Server identifiers use; rejects quotes, semicolons, whitespace runs,
# and anything that could break out of the statement (defense-in-depth — the names
# come from the user's own config/catalog, but we never trust them blindly).
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$#]*$")


def assert_identifier(*names: str) -> None:
    """Raise ValueError if any name is not a safe SQL identifier."""
    for name in names:
        if not name or not _IDENT_RE.match(name):
            raise ValueError(
                f"unsafe or invalid SQL identifier: {name!r} "
                "(expected letters/digits/_/$/# starting with a letter or _)")


# ---- engine-neutral data structures --------------------------------------

# Order in which an object-unit's components are concatenated for the LLM prompt.
_COMPONENT_ORDER = [
    ("table", "TABLE"),
    ("constraints", "CONSTRAINTS (PK / UNIQUE / CHECK)"),
    ("indexes", "INDEXES"),
    ("ref_constraints", "FOREIGN KEYS"),
    ("triggers", "TRIGGERS"),
    ("comments", "COMMENTS"),
    ("grants", "GRANTS"),
]


@dataclass
class ObjectUnit:
    """A table together with its indexes, constraints, FKs, triggers, comments
    and grants — converted holistically as one unit."""
    schema: str
    name: str
    components: Dict[str, str] = field(default_factory=dict)
    num_rows: int = -1

    @property
    def source_ddl(self) -> str:
        parts: List[str] = []
        for key, label in _COMPONENT_ORDER:
            body = (self.components.get(key) or "").strip()
            if body:
                parts.append(f"-- === {label} ===\n{body}")
        return "\n\n".join(parts).strip()

    def is_small(self, row_threshold: int) -> bool:
        return self.num_rows < 0 or self.num_rows <= row_threshold


@dataclass
class CodeObject:
    schema: str
    object_type: str
    name: str
    source_ddl: str


def batch_units(units: List[ObjectUnit], row_threshold: int,
                max_units: int) -> List[List[ObjectUnit]]:
    """Group small tables into shared batches; large tables get their own batch."""
    batches: List[List[ObjectUnit]] = []
    bucket: List[ObjectUnit] = []

    def flush() -> None:
        if bucket:
            batches.append(list(bucket))
            bucket.clear()

    for unit in units:
        if unit.is_small(row_threshold):
            bucket.append(unit)
            if len(bucket) >= max_units:
                flush()
        else:
            flush()
            batches.append([unit])
    flush()
    return batches


def topological_tiers(names: List[str],
                      deps: Dict[str, set]) -> List[List[str]]:
    """Order ``names`` into dependency tiers given ``deps`` (table -> set of
    tables it references). Tier 0 has no in-scope dependencies; each later tier
    depends only on earlier tiers — safe load order for foreign keys. A
    dependency cycle is emitted as one final tier (best effort)."""
    nameset = set(names)
    remaining = {n: (set(deps.get(n, set())) & nameset) - {n} for n in names}
    placed: set = set()
    tiers: List[List[str]] = []
    while len(placed) < len(names):
        tier = [n for n in names if n not in placed and remaining[n] <= placed]
        if not tier:  # cycle — emit whatever is left together
            tier = [n for n in names if n not in placed]
        tiers.append(tier)
        placed.update(tier)
    return tiers


# ---- common engine behavior ----------------------------------------------

class Engine(ABC):
    """Shared connection lifecycle + generic DB-API helpers.

    ``model`` is a ``connections.Connection`` describing how to connect.
    """

    role = "engine"

    def __init__(self, model) -> None:
        self.model = model
        self._conn = None

    @property
    def engine(self) -> str:
        return self.model.engine

    # ---- connection lifecycle ----
    @abstractmethod
    def connect(self):
        """Open and return a new DB-API connection for ``self.model``."""

    @property
    def connection(self):
        if self._conn is None:
            self._conn = self.connect()
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        self.close()
        return False

    # ---- generic DB-API helpers (work for oracledb / psycopg / pymysql) ----
    @abstractmethod
    def ping_sql(self) -> str:
        """A trivial query that returns 1 (e.g. 'SELECT 1' or 'SELECT 1 FROM dual')."""

    @abstractmethod
    def server_version(self) -> str:
        ...

    def ping(self) -> bool:
        return self.scalar(self.ping_sql()) == 1

    def scalar(self, sql: str, params: Optional[dict] = None):
        cur = self.connection.cursor()
        try:
            cur.execute(sql, params or {}) if params else cur.execute(sql)
            if cur.description:
                row = cur.fetchone()
                return row[0] if row else None
            return None
        finally:
            cur.close()

    def execute(self, sql: str, params: Optional[dict] = None) -> None:
        cur = self.connection.cursor()
        try:
            cur.execute(sql, params or {}) if params else cur.execute(sql)
        finally:
            cur.close()

    def fetch(self, sql: str, params: Optional[dict] = None) -> Tuple[List[str], List[tuple]]:
        """Run a query; return (column_names, rows). Loads all rows — use
        ``fetch_iter`` for large result sets to keep memory bounded."""
        cur = self.connection.cursor()
        try:
            cur.execute(sql, params or {}) if params else cur.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall() if cur.description else []
            return cols, rows
        finally:
            cur.close()

    def fetch_iter(self, sql: str, params: Optional[dict] = None,
                   arraysize: int = 5000) -> Iterator[tuple]:
        """Stream rows via server-side ``fetchmany`` so a large chunk never fully
        materializes in memory. Yields rows one at a time."""
        cur = self.connection.cursor()
        try:
            try:
                cur.arraysize = arraysize
            except Exception:
                pass
            cur.execute(sql, params or {}) if params else cur.execute(sql)
            if not cur.description:
                return
            while True:
                rows = cur.fetchmany(arraysize)
                if not rows:
                    break
                for row in rows:
                    yield row
        finally:
            cur.close()

    def rollback(self) -> None:
        try:
            self.connection.rollback()
        except Exception:
            pass

    def commit(self) -> None:
        try:
            self.connection.commit()
        except Exception:
            pass


class SourceEngine(Engine, ABC):
    """Read-side adapter: inventory, DDL extraction, sampling, chunked extraction."""

    role = "source"

    @abstractmethod
    def list_tables(self, schema: str, only: Optional[List[str]] = None) -> List[str]:
        ...

    @abstractmethod
    def get_table_list(self, schema: str) -> List[Dict[str, Any]]:
        """[{name, row_count, columns}] for inventory."""

    @abstractmethod
    def extract_object_unit(self, schema: str, table: str) -> ObjectUnit:
        """One table + its indexes/constraints/FKs/triggers/comments/grants."""

    def extract_object_unit_ddl(self, schema: str, table: str) -> str:
        """The object-unit as one DDL block (CREATE TABLE + indexes + constraints
        + FKs + triggers + comments/grants), per the adapter contract."""
        return self.extract_object_unit(schema, table).source_ddl

    def extract_units(self, schema: str,
                      tables: Optional[List[str]] = None) -> List[ObjectUnit]:
        units: List[ObjectUnit] = []
        for table in self.list_tables(schema, only=tables):
            unit = self.extract_object_unit(schema, table)
            if (unit.components.get("table") or "").strip():
                units.append(unit)
        return units

    @abstractmethod
    def extract_code_objects(self, schema: str) -> List[CodeObject]:
        ...

    @abstractmethod
    def list_callables(self, schema: str) -> List[Tuple[str, str]]:
        ...

    @abstractmethod
    def code_object_ddl(self, schema: str, object_type: str, name: str) -> str:
        ...

    @abstractmethod
    def sample_rows(self, schema: str, table: str, n: int = 5):
        """Return (columns, rows) of up to n REAL rows."""

    @abstractmethod
    def primary_key_columns(self, schema: str, table: str) -> List[str]:
        ...

    @abstractmethod
    def table_columns(self, schema: str, table: str) -> List[Tuple[str, str]]:
        ...

    @abstractmethod
    def chunk_iterator(self, schema: str, table: str, pk_cols: List[str],
                       batch_size: int) -> Iterator[Tuple[str, dict]]:
        """Yield (query, params) tuples for chunked data extraction.

        Range-based on a single numeric PK (parallelizable); a single full-table
        chunk otherwise.
        """

    @abstractmethod
    def inventory(self, schema: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def count_rows(self, schema: str, table: str) -> int:
        """Exact COUNT(*) for reconciliation."""

    @abstractmethod
    def foreign_key_deps(self, schema: str, tables: List[str]) -> Dict[str, set]:
        """Return {table: set(referenced_tables)} for foreign keys among the given
        (upper-cased) tables — used to order data loads so parents load first."""

    def package_routines(self, schema: str) -> List[Dict[str, Any]]:
        """Package subprograms + standalone routines, for package-flattening
        naming-conflict checks. Each item: {package: str|None, name: str,
        kind: str, overload: str|None}. Default: none (engines without
        packages, e.g. SQL Server)."""
        return []


class TargetEngine(Engine, ABC):
    """Write-side adapter: schema/DDL apply and fast ingestion."""

    role = "target"

    @abstractmethod
    def table_exists(self, schema: str, table: str):
        """Return True/False if the engine can check the catalog, else None
        (= cannot verify). Used by apply-schema's post-apply verification to
        detect DDL that applied cleanly into the WRONG schema/database."""
        return None

    def ensure_schema(self, schema: str) -> None:
        ...

    @abstractmethod
    def _apply_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """Apply one SQL unit in its own transaction; return (ok, error)."""

    def apply_ddl(self, sql: str) -> None:
        """Apply a single DDL block; raise on failure."""
        ok, err = self._apply_sql(sql)
        if not ok:
            raise RuntimeError(err)

    def apply_units(self, files: Sequence[Tuple[str, str]],
                    max_passes: int = 5) -> List[Dict[str, Any]]:
        """Apply (label, sql) units with multi-pass ordering resolution."""
        return _common.multipass_apply(
            lambda _conn, sql: self._apply_sql(sql), self.connection, files,
            max_passes)

    @abstractmethod
    def bulk_insert(self, schema: str, table: str, columns: Sequence[str],
                    rows) -> int:
        """Fast ingestion (COPY protocol or batched executemany). Return rows written."""

    @abstractmethod
    def get_row_count(self, schema: str, table: str) -> int:
        ...

    @abstractmethod
    def truncate(self, schema: str, table: str) -> None:
        ...

    @abstractmethod
    def primary_key_columns(self, schema: str, table: str) -> List[str]:
        ...

    def reset_identity(self, schema: str, table: str) -> None:
        """Advance identity / AUTO_INCREMENT to MAX(key) after a data load so the
        next generated key does not collide with migrated rows. Default no-op;
        target engines override as needed."""
        return

    def target_columns(self, schema: str, table: str) -> List[str]:
        """Return the existing target table's column names (lower-cased, ordinal
        order). Used to validate source->target column alignment before a data
        copy. Works for both PostgreSQL and MySQL targets via information_schema
        (both use the ``%s`` param style). Returns [] if the table is absent."""
        _, rows = self.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s "
            "ORDER BY ordinal_position",
            (schema, table))
        return [str(r[0]).lower() for r in rows]
