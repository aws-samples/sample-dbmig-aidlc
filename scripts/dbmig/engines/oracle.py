"""Oracle source helpers: catalog inventory, DDL extraction, code objects.

Uses an open ``oracledb`` (thin-mode) connection. DDL is extracted with
``DBMS_METADATA`` so the output reflects exactly what the source defines.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from . import _common


def server_version(conn) -> str:
    cur = conn.cursor()
    try:
        cur.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
        row = cur.fetchone()
        return row[0] if row else "unknown"
    except Exception:
        return getattr(conn, "version", "unknown")
    finally:
        cur.close()


def _set_metadata_transform(conn) -> None:
    """Make DBMS_METADATA output clean, portable DDL (best-effort)."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            BEGIN
              DBMS_METADATA.SET_TRANSFORM_PARAM(
                DBMS_METADATA.SESSION_TRANSFORM, 'PRETTY', TRUE);
              DBMS_METADATA.SET_TRANSFORM_PARAM(
                DBMS_METADATA.SESSION_TRANSFORM, 'SQLTERMINATOR', TRUE);
              DBMS_METADATA.SET_TRANSFORM_PARAM(
                DBMS_METADATA.SESSION_TRANSFORM, 'SEGMENT_ATTRIBUTES', FALSE);
              DBMS_METADATA.SET_TRANSFORM_PARAM(
                DBMS_METADATA.SESSION_TRANSFORM, 'STORAGE', FALSE);
              DBMS_METADATA.SET_TRANSFORM_PARAM(
                DBMS_METADATA.SESSION_TRANSFORM, 'TABLESPACE', FALSE);
              DBMS_METADATA.SET_TRANSFORM_PARAM(
                DBMS_METADATA.SESSION_TRANSFORM, 'CONSTRAINTS_AS_ALTER', TRUE);
              DBMS_METADATA.SET_TRANSFORM_PARAM(
                DBMS_METADATA.SESSION_TRANSFORM, 'REF_CONSTRAINTS', FALSE);
            END;
            """
        )
    except Exception:
        # Defaults still produce valid DDL if the session transform can't be set.
        pass
    finally:
        cur.close()


def _read(val) -> str:
    if val is None:
        return ""
    if hasattr(val, "read"):
        return val.read()
    return str(val)


def foreign_key_pairs(conn, schema: str):
    """Return [(child_table, parent_table)] for FK (R) constraints in the schema."""
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT c.table_name, r.table_name "
            "FROM all_constraints c "
            "JOIN all_constraints r ON c.r_owner = r.owner "
            " AND c.r_constraint_name = r.constraint_name "
            "WHERE c.owner = :o AND c.constraint_type = 'R' AND r.owner = :o",
            o=schema.upper(),
        )
        return [(row[0], row[1]) for row in cur.fetchall()]
    except Exception:
        return []
    finally:
        cur.close()


def package_routines(conn, schema: str):
    """Return [{package, name, kind, overload}] for package subprograms and
    standalone procedures/functions in the schema, from ALL_PROCEDURES — used to
    detect package-flattening naming conflicts."""
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT object_name, procedure_name, object_type, overload "
            "FROM all_procedures "
            "WHERE owner = :o AND object_type IN ('PACKAGE','PROCEDURE','FUNCTION')",
            o=schema.upper(),
        )
        rows = cur.fetchall()
    except Exception:
        return []
    finally:
        cur.close()

    out = []
    seen_standalone = set()
    for object_name, procedure_name, object_type, overload in rows:
        if object_type == "PACKAGE":
            if procedure_name:  # skip the package-init row (NULL procedure_name)
                out.append({"package": object_name, "name": procedure_name,
                            "kind": "PACKAGE_ROUTINE", "overload": overload})
        elif object_name not in seen_standalone:
            seen_standalone.add(object_name)
            out.append({"package": None, "name": object_name,
                        "kind": object_type, "overload": overload})
    return out


def list_tables(conn, schema: str, only: Optional[List[str]] = None) -> List[str]:
    cur = conn.cursor()
    try:
        # Exclude Oracle-generated secondary/internal tables that show up in
        # all_tables but are not user objects: Oracle Text (CONTEXT) index tables
        # (DR$...), materialized-view logs (MLOG$/RUPD$), and IOT overflow segments.
        sql = ("SELECT table_name FROM all_tables "
               "WHERE owner = :owner "
               "  AND table_name NOT LIKE 'DR$%' "
               "  AND table_name NOT LIKE 'MLOG$%' "
               "  AND table_name NOT LIKE 'RUPD$%' "
               "  AND table_name NOT LIKE 'SYS_IOT_OVER_%' "
               "  AND nested = 'NO' "
               "  AND (secondary = 'N' OR secondary IS NULL) "
               "ORDER BY table_name")
        cur.execute(sql, owner=schema.upper())
        tables = [r[0] for r in cur.fetchall()]
    finally:
        cur.close()
    if only:
        wanted = {t.upper() for t in only}
        tables = [t for t in tables if t.upper() in wanted]
    return tables


def table_row_estimate(conn, schema: str, table: str) -> int:
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT NVL(num_rows, -1) FROM all_tables "
            "WHERE owner = :o AND table_name = :t",
            o=schema.upper(), t=table.upper(),
        )
        row = cur.fetchone()
        return int(row[0]) if row else -1
    finally:
        cur.close()


def primary_key_columns(conn, schema: str, table: str) -> List[str]:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT cc.column_name
            FROM all_constraints c
            JOIN all_cons_columns cc
              ON c.owner = cc.owner AND c.constraint_name = cc.constraint_name
            WHERE c.owner = :o AND c.table_name = :t AND c.constraint_type = 'P'
            ORDER BY cc.position
            """,
            o=schema.upper(), t=table.upper(),
        )
        return [r[0] for r in cur.fetchall()]
    finally:
        cur.close()


def table_columns(conn, schema: str, table: str) -> List[Tuple[str, str]]:
    """Return [(column_name, data_type)] in column order."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM all_tab_columns
            WHERE owner = :o AND table_name = :t
            ORDER BY column_id
            """,
            o=schema.upper(), t=table.upper(),
        )
        return [(r[0], r[1]) for r in cur.fetchall()]
    finally:
        cur.close()


def _get_ddl(conn, object_type: str, name: str, schema: str) -> str:
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT DBMS_METADATA.GET_DDL(:typ, :name, :owner) FROM dual",
            typ=object_type, name=name, owner=schema.upper(),
        )
        row = cur.fetchone()
        return _read(row[0]).strip() if row else ""
    except Exception:
        return ""
    finally:
        cur.close()


def _get_dependent_ddl(conn, object_type: str, table: str, schema: str) -> str:
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT DBMS_METADATA.GET_DEPENDENT_DDL(:typ, :name, :owner) FROM dual",
            typ=object_type, name=table.upper(), owner=schema.upper(),
        )
        row = cur.fetchone()
        return _read(row[0]).strip() if row else ""
    except Exception:
        # ORA-31608 is raised when there are no dependent objects of that type.
        return ""
    finally:
        cur.close()


def object_unit_ddl(conn, schema: str, table: str) -> Dict[str, str]:
    """Extract a table's full object-unit DDL grouped by component.

    Components: table, indexes, constraints (PK/UK/CHECK), ref_constraints (FK),
    triggers, comments, grants. Missing components return ''.
    """
    _set_metadata_transform(conn)
    sch = schema.upper()
    tbl = table.upper()
    return {
        "table": _get_ddl(conn, "TABLE", tbl, sch),
        "indexes": _get_dependent_ddl(conn, "INDEX", tbl, sch),
        "constraints": _get_dependent_ddl(conn, "CONSTRAINT", tbl, sch),
        "ref_constraints": _get_dependent_ddl(conn, "REF_CONSTRAINT", tbl, sch),
        "triggers": _get_dependent_ddl(conn, "TRIGGER", tbl, sch),
        "comments": _get_dependent_ddl(conn, "COMMENT", tbl, sch),
        "grants": _get_dependent_ddl(conn, "OBJECT_GRANT", tbl, sch),
    }


# ---- code objects (separate conversion pass) ------------------------------

CODE_OBJECT_TYPES = [
    "PACKAGE", "PACKAGE BODY", "PROCEDURE", "FUNCTION", "TYPE", "TYPE BODY",
]


def build_list_code_objects_sql() -> str:
    """SELECT for PL/SQL code objects. The IN-list is built from the trusted
    module constant CODE_OBJECT_TYPES (not user input); owner is a bind (:o)."""
    placeholders = ", ".join(f"'{t}'" for t in CODE_OBJECT_TYPES)
    return f"SELECT object_type, object_name FROM all_objects WHERE owner = :o AND object_type IN ({placeholders}) ORDER BY object_type, object_name"  # nosec B608


def list_code_objects(conn, schema: str) -> List[Tuple[str, str]]:
    """Return [(object_type, object_name)] for PL/SQL code objects."""
    cur = conn.cursor()
    try:
        cur.execute(build_list_code_objects_sql(), o=schema.upper())
        return [(r[0], r[1]) for r in cur.fetchall()]
    finally:
        cur.close()


_DDL_TYPE_MAP = {
    "PACKAGE": "PACKAGE",
    "PACKAGE BODY": "PACKAGE_BODY",
    "TYPE": "TYPE",
    "TYPE BODY": "TYPE_BODY",
    "PROCEDURE": "PROCEDURE",
    "FUNCTION": "FUNCTION",
}


def code_object_ddl(conn, schema: str, object_type: str, name: str) -> str:
    meta_type = _DDL_TYPE_MAP.get(object_type, object_type.replace(" ", "_"))
    return _get_ddl(conn, meta_type, name, schema)


# ---- callables + real-data sampling (for equivalence testing) -------------

def list_callables(conn, schema: str) -> List[Tuple[str, str]]:
    """Return [(object_type, name)] for testable callables: functions, procedures,
    and packages (whose public subprograms Kiro can target in test specs)."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT object_type, object_name
            FROM all_objects
            WHERE owner = :o AND object_type IN ('FUNCTION', 'PROCEDURE', 'PACKAGE')
            ORDER BY object_type, object_name
            """,
            o=schema.upper(),
        )
        return [(r[0], r[1]) for r in cur.fetchall()]
    finally:
        cur.close()


def build_sample_rows_sql(schema: str, table: str, n: int) -> str:
    """Build a 'SELECT * ... FETCH FIRST n ROWS ONLY' statement for sampling.

    Identifiers cannot be bound parameters, so they are validated against a
    strict allowlist (``assert_identifier``) before interpolation; ``n`` is
    coerced to a positive int. See SECURITY.md ("SQL construction").
    """
    assert_identifier(schema, table)
    n = max(1, int(n))
    return f"SELECT * FROM {schema}.{table} FETCH FIRST {n} ROWS ONLY"  # nosec B608


def sample_rows(conn, schema: str, table: str, n: int = 5):
    """Return (columns, rows) of up to ``n`` REAL rows from a source table.

    Used to ground test-case generation in data that actually exists, so the
    generated tests reference real keys/values rather than invented ones.
    """
    sql = build_sample_rows_sql(schema, table, n)
    cur = conn.cursor()
    try:
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return cols, rows
    except Exception:
        return [], []
    finally:
        cur.close()


# ---- inventory ------------------------------------------------------------

def inventory(conn, schema: str) -> Dict[str, Any]:
    """Structured inventory of a schema for the assessment phase."""
    cur = conn.cursor()
    sch = schema.upper()
    result: Dict[str, Any] = {"schema": sch}
    try:
        cur.execute(
            "SELECT object_type, COUNT(*) FROM all_objects "
            "WHERE owner = :o GROUP BY object_type ORDER BY object_type",
            o=sch,
        )
        result["object_counts"] = {r[0]: int(r[1]) for r in cur.fetchall()}

        cur.execute(
            """
            SELECT t.table_name, NVL(t.num_rows, -1),
                   (SELECT COUNT(*) FROM all_tab_columns c
                    WHERE c.owner = t.owner AND c.table_name = t.table_name)
            FROM all_tables t WHERE t.owner = :o ORDER BY t.table_name
            """,
            o=sch,
        )
        result["tables"] = [
            {"name": r[0], "num_rows": int(r[1]), "columns": int(r[2])}
            for r in cur.fetchall()
        ]

        cur.execute(
            "SELECT data_type, COUNT(*) FROM all_tab_columns "
            "WHERE owner = :o GROUP BY data_type ORDER BY COUNT(*) DESC",
            o=sch,
        )
        result["datatypes"] = {r[0]: int(r[1]) for r in cur.fetchall()}

        cur.execute(
            "SELECT type, name, MAX(line) FROM all_source "
            "WHERE owner = :o GROUP BY type, name ORDER BY MAX(line) DESC",
            o=sch,
        )
        result["code_units"] = [
            {"type": r[0], "name": r[1], "lines": int(r[2])} for r in cur.fetchall()
        ]

        # Cross-schema dependencies: objects in this schema that reference objects in
        # OTHER (non-system) schemas — surfaced so a partial migration sees out-of-scope
        # dependencies up front. (ALL_DEPENDENCIES; SYS/SYSTEM/PUBLIC filtered out.)
        try:
            cur.execute(
                "SELECT name, referenced_owner, referenced_name FROM all_dependencies "
                "WHERE owner = :o AND referenced_owner IS NOT NULL "
                "AND referenced_owner <> :o "
                "AND referenced_owner NOT IN ('SYS','SYSTEM','PUBLIC','XDB','MDSYS','CTXSYS')",
                o=sch,
            )
            result["cross_schema_dependencies"] = _common.summarize_cross_schema_deps(
                [(r[0], r[1], r[2]) for r in cur.fetchall()], sch)
        except Exception:
            result["cross_schema_dependencies"] = []
    finally:
        cur.close()
    return result


# ---- adapter -------------------------------------------------------------

from numbers import Number as _Number  # noqa: E402

from .. import connections as _connections  # noqa: E402
from .base import CodeObject, ObjectUnit, SourceEngine, assert_identifier  # noqa: E402


class OracleEngine(SourceEngine):
    """Oracle source adapter (oracledb thin mode)."""

    def connect(self):
        return _connections.db_connect(self.model)

    def ping_sql(self) -> str:
        return "SELECT 1 FROM dual"

    def server_version(self) -> str:
        return server_version(self.connection)

    def list_tables(self, schema, only=None):
        return list_tables(self.connection, schema, only=only)

    def get_table_list(self, schema):
        inv = inventory(self.connection, schema)
        return [{"name": t["name"], "row_count": t["num_rows"],
                 "columns": t["columns"]} for t in inv.get("tables", [])]

    def extract_object_unit(self, schema, table) -> ObjectUnit:
        return ObjectUnit(
            schema=schema.upper(), name=table,
            components=object_unit_ddl(self.connection, schema, table),
            num_rows=table_row_estimate(self.connection, schema, table))

    def extract_code_objects(self, schema):
        out = []
        for object_type, name in list_code_objects(self.connection, schema):
            ddl = code_object_ddl(self.connection, schema, object_type, name)
            if ddl.strip():
                out.append(CodeObject(schema.upper(), object_type, name, ddl))
        return out

    def list_callables(self, schema):
        return list_callables(self.connection, schema)

    def code_object_ddl(self, schema, object_type, name):
        return code_object_ddl(self.connection, schema, object_type, name)

    def sample_rows(self, schema, table, n=5):
        assert_identifier(schema, table)
        return sample_rows(self.connection, schema, table, n=n)

    def primary_key_columns(self, schema, table):
        return primary_key_columns(self.connection, schema, table)

    def table_columns(self, schema, table):
        return table_columns(self.connection, schema, table)

    def chunk_iterator(self, schema, table, pk_cols, batch_size):
        # Identifiers are interpolated (not bound), so validate them. Oracle is
        # case-insensitive for unquoted names, so schema/table stay unquoted to
        # preserve the catalog's folding behavior.
        assert_identifier(schema, table, *pk_cols)
        cols = [c for c, _ in self.table_columns(schema, table)]
        col_list = ", ".join(f'"{c}"' for c in cols) or "*"
        base = f"SELECT {col_list} FROM {schema}.{table}"  # nosec B608
        if len(pk_cols) == 1:
            pk = pk_cols[0]
            lo = self.scalar(f'SELECT MIN("{pk}") FROM {schema}.{table}')  # nosec B608
            hi = self.scalar(f'SELECT MAX("{pk}") FROM {schema}.{table}')  # nosec B608
            if isinstance(lo, _Number) and isinstance(hi, _Number) and hi >= lo:
                lo_i, hi_i = int(lo), int(hi)
                step = max(1, int(batch_size))
                cur = lo_i
                while cur <= hi_i:
                    yield (f'{base} WHERE "{pk}" >= :lo AND "{pk}" < :hi '
                           f'ORDER BY "{pk}"', {"lo": cur, "hi": cur + step})
                    cur += step
                return
        # Fallback: a single full-table chunk (non-numeric / composite / no PK).
        yield (base, {})

    def inventory(self, schema):
        return inventory(self.connection, schema)

    def count_rows(self, schema, table):
        assert_identifier(schema, table)
        return int(self.scalar(f"SELECT COUNT(*) FROM {schema}.{table}") or 0)  # nosec B608

    def foreign_key_deps(self, schema, tables):
        up = {t.upper() for t in tables}
        deps = {t: set() for t in up}
        for child, parent in foreign_key_pairs(self.connection, schema):
            c, p = child.upper(), parent.upper()
            if c in up and p in up and c != p:
                deps[c].add(p)
        return deps

    def package_routines(self, schema):
        return package_routines(self.connection, schema)
