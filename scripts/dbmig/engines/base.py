"""Engine adapter base classes and engine-neutral data structures.

The dbmig commands depend ONLY on these interfaces (resolved via
``engines.registry``); they never import engine-specific modules directly. To add
a new engine, implement ``SourceEngine`` and/or ``TargetEngine`` in a new module
and register it in ``engines/registry.py``.
"""
from __future__ import annotations

import contextlib

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
    # Engine-emitted advisories (SQL comments only, never executable DDL): e.g.
    # an Oracle Text domain index that needs a design decision, not a 1:1 port.
    ("advisories", "ADVISORIES (not DDL — decisions required before converting)"),
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


def batch_by_size(items, size_of, *, max_items: int, max_bytes: int,
                  key_of=None) -> List[list]:
    """Group consecutive small items into shared prompts (order preserved).

    An item larger than ``max_bytes`` gets its own batch; a batch closes at
    ``max_items`` or ``max_bytes`` of source, or when ``key_of`` changes (e.g. the
    code dependency tier, so a batch never mixes tiers). Fewer, fuller prompts
    mean fewer per-prompt instruction/reference repeats and far fewer file reads
    on schemas with hundreds or thousands of objects."""
    batches: List[list] = []
    cur: list = []
    cur_bytes = 0
    cur_key = object()
    for it in items:
        sz = max(0, int(size_of(it)))
        k = key_of(it) if key_of else None
        if cur and (k != cur_key or len(cur) >= max_items or cur_bytes + sz > max_bytes):
            batches.append(cur)
            cur, cur_bytes = [], 0
        if sz > max_bytes:
            batches.append([it])
            cur_key = object()
            continue
        cur.append(it)
        cur_bytes += sz
        cur_key = k
    if cur:
        batches.append(cur)
    return batches


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
            with contextlib.suppress(Exception):   # closing a dead connection
                self._conn.close()
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

    def preflight_warnings(self) -> List[str]:
        """Target-specific settings that make a migration unsafe or misleading (shown by
        ``test-connection``). Engines override; the default has none."""
        return []

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
            with contextlib.suppress(Exception):   # driver without arraysize
                cur.arraysize = arraysize
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
        # Best effort: rollback runs on error paths where the connection may
        # already be broken; the original error is what matters.
        with contextlib.suppress(Exception):
            self.connection.rollback()

    def commit(self) -> None:
        # A failed COMMIT means the work was NOT persisted — never swallow it.
        self.connection.commit()


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

    def set_session_schema(self, schema: str) -> None:
        """Make unqualified names resolve to ``schema`` for this session, so test
        probes work when the login user is not the schema owner (e.g. Oracle
        ``admin`` vs owner ``DEMO``). Default no-op (engines without a session
        schema switch, e.g. SQL Server, where the default schema is per-user)."""
        return

    def standalone_sequences(self, schema: str) -> List[Dict[str, Any]]:
        """User-defined sequences NOT backing an identity column —
        ``[{name, last_value}]``. These are not handled by identity reset and
        must be synced to the source value at cutover. Default: none."""
        return []

    @abstractmethod
    def primary_key_columns(self, schema: str, table: str) -> List[str]:
        ...

    @abstractmethod
    def table_columns(self, schema: str, table: str) -> List[Tuple[str, str]]:
        ...

    def virtual_columns(self, schema: str, table: str) -> set:
        """Return the set of column names (in the source catalog's case, matching
        ``table_columns``) that are VIRTUAL / computed on the source — their value
        is derived from an expression rather than stored.

        These MUST be excluded from data movement: the converted target defines
        such a column as a GENERATED column, and both PostgreSQL COPY and MySQL
        INSERT reject writing an explicit value into a generated column (the copy
        fails on the whole table). Even where the target keeps it as a plain
        column, copying a derived value is redundant — the source value is not
        independent data. Default: none (engines without virtual columns)."""
        return set()

    def data_columns(self, schema: str, table: str) -> List[Tuple[str, str]]:
        """``table_columns`` with VIRTUAL / computed columns removed — the columns
        that carry stored data and are therefore the ones copied during a data
        load. Matching is case-insensitive so it is robust to catalog case folding.

        All data-movement paths (toolkit ``chunk_iterator`` SELECT lists,
        ``migrate_data`` target column alignment, and the FDW ``INSERT ... SELECT``)
        use this instead of ``table_columns`` so generated target columns are never
        written to."""
        virtual = {c.lower() for c in self.virtual_columns(schema, table)}
        if not virtual:
            return self.table_columns(schema, table)
        return [(name, typ) for name, typ in self.table_columns(schema, table)
                if name.lower() not in virtual]

    @abstractmethod
    def chunk_iterator(self, schema: str, table: str, pk_cols: List[str],
                       batch_size: int, pk_lo: Optional[int] = None,
                       pk_hi: Optional[int] = None) -> Iterator[Tuple[str, dict]]:
        """Yield (query, params) tuples for chunked data extraction.

        Range-based on a single numeric PK (parallelizable); a single full-table
        chunk otherwise. When ``pk_lo``/``pk_hi`` are given (a shard sub-range of a
        single numeric PK), chunk only within ``[pk_lo, pk_hi)`` — this is how
        intra-table sharding hands each parallel reader a disjoint PK slice.
        """

    def numeric_pk_bounds(self, schema: str, table: str,
                          pk: str) -> Optional[Tuple[int, int]]:
        """Return (min, max) of a single numeric PK column for intra-table
        sharding, or ``None`` when the table is not shardable this way (non-numeric
        / composite / no PK). Default: not shardable."""
        return None

    def row_estimate(self, schema: str, table: str) -> int:
        """Best-effort estimated row count from the source's own optimizer
        statistics (cheap catalog read, no COUNT(*)). Returns -1 when unknown.

        Used to size chunking/sharding by *rows* rather than by PK span alone: a
        wide but sparse PK range (e.g. an IDENTITY that has recycled/large seed
        values, so keys run 1..200,000,000 for only 100,000 live rows) would
        otherwise be sliced into thousands of near-empty key-range chunks. Default:
        unknown."""
        return -1

    def _adaptive_chunk_step(self, lo: int, hi: int, batch_size: int,
                             estimate: int) -> int:
        """Key-space step for range chunking that targets ~``batch_size`` ROWS per
        chunk, not ``batch_size`` KEY VALUES.

        When the PK is dense (span ≈ rows) this returns ``batch_size`` unchanged —
        identical to the previous behaviour. When the PK range is sparse relative to
        the estimated row count (``span > estimate``), the step is widened by the
        density factor ``span / estimate`` so each chunk still spans about
        ``batch_size`` real rows. This collapses the "200M-wide range, 100k rows"
        case from ~thousands of empty chunks to a handful of populated ones. The
        step is never smaller than ``batch_size`` and never larger than the span."""
        batch_size = max(1, int(batch_size))
        span = hi - lo + 1
        if span <= 0:
            return batch_size
        if estimate and estimate > 0 and span > estimate:
            # rows-per-key < 1 (sparse); scale the step up to keep ~batch_size rows.
            step = int(batch_size * (span / estimate))
            return max(batch_size, min(step, span))
        return batch_size

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

    # ---- FDW push-down descriptor (PostgreSQL target pulls directly) --------
    # These describe how a PostgreSQL target can read THIS source directly via a
    # foreign data wrapper, so ``migrate-data --method fdw`` can move data
    # server-side (target <- source) instead of pulling every row through the
    # toolkit host. Default: not FDW-capable. Oracle and SQL Server override.

    def fdw_wrapper(self) -> Optional[str]:
        """Name of the PostgreSQL foreign-data-wrapper *extension* that reads this
        source — ``'oracle_fdw'`` / ``'tds_fdw'`` — or ``None`` if push-down load
        is not supported for this source engine."""
        return None

    def fdw_server_options(self) -> Dict[str, str]:
        """OPTIONS for ``CREATE SERVER`` (how the wrapper reaches this source)."""
        return {}

    def fdw_user_mapping_options(self) -> Dict[str, str]:
        """OPTIONS for ``CREATE USER MAPPING`` — the source credentials the target
        uses to connect. These are written into the target catalog, so the loader
        drops the mapping after the load unless told to keep it."""
        return {}

    def fdw_foreign_table_options(self, schema: str, table: str) -> Dict[str, str]:
        """Per-table OPTIONS for ``CREATE FOREIGN TABLE`` (which remote table to
        map, and any wrapper-specific read tuning)."""
        return {}

    def fdw_column_decl(self, target_type: str) -> Tuple[str, Optional[str]]:
        """Given a TARGET column type (PostgreSQL ``format_type`` string), return
        ``(foreign_declared_type, select_template)`` for the foreign-table column
        that maps to it. ``select_template`` is either ``None`` (select the foreign
        column directly) or a string containing ``{col}`` that produces the SELECT
        expression (e.g. a target-side ``CAST``/normalization). Default: declare the
        foreign column with the target type and select it directly."""
        return (target_type, None)


class TargetEngine(Engine, ABC):
    """Write-side adapter: schema/DDL apply and fast ingestion."""

    role = "target"

    # True only for targets that can pull directly from a source via a foreign
    # data wrapper (``migrate-data --method fdw``). PostgreSQL sets this True and
    # implements the fdw_* DDL helpers + ``target_column_types``; MySQL leaves it
    # False (no heterogeneous FDW), so the loader can guard with a clear error.
    fdw_capable = False

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

    def identity_columns(self, schema: str) -> List[Dict[str, Any]]:
        """Every identity/serial/AUTO_INCREMENT-backed column in ``schema``:
        ``[{table, column, sequence}]`` (``sequence`` may be None for engines
        without sequences). Used by ``dbmig reset-identity``. Default: none."""
        return []

    def identity_state(self, schema: str, table: str, column: str,
                       sequence: Optional[str]) -> Dict[str, Any]:
        """Current ``{max_id, next_value}`` for one identity column — the value
        the NEXT generated key would take. Default: unknown."""
        return {"max_id": None, "next_value": None}

    def sync_identity(self, schema: str, table: str, column: str,
                      sequence: Optional[str]) -> None:
        """Set one identity so its next value is ``MAX(column)+1`` (or its start
        value when the table is empty). Default no-op."""
        return

    def standalone_sequences(self, schema: str) -> List[Dict[str, Any]]:
        """Sequences in ``schema`` NOT owned by a column — ``[{name, last_value}]``
        (need a manual source-value sync at cutover). Default: none."""
        return []

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
