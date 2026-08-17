"""PostgreSQL target helpers: apply DDL, COPY ingestion, counts, introspection.

Uses an open ``psycopg`` (v3) connection.
"""
from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence, Tuple


# ---- safe SQL construction ------------------------------------------------
# Identifiers (schema/table/column) cannot be passed as bound query parameters,
# so they are quoted here before interpolation. These builders centralize that
# quoting and return a finished SQL string; callers pass the returned string to
# the driver, and all *data values* are passed as bound parameters (never
# formatted). See SECURITY.md ("SQL construction").

def _quote_ident(name: str) -> str:
    """Quote a PostgreSQL identifier, doubling any embedded double-quotes."""
    return '"' + str(name).replace('"', '""') + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_quote_ident(schema)}.{_quote_ident(table)}"


def build_create_schema_sql(schema: str) -> str:
    return f"CREATE SCHEMA IF NOT EXISTS {_quote_ident(schema)}"  # nosec B608


def build_row_count_sql(schema: str, table: str) -> str:
    return f"SELECT COUNT(*) FROM {_qualified(schema, table)}"  # nosec B608


def build_truncate_sql(schema: str, table: str) -> str:
    return f"TRUNCATE TABLE {_qualified(schema, table)}"  # nosec B608


def build_copy_sql(schema: str, table: str, columns: Sequence[str]) -> str:
    col_list = ", ".join(_quote_ident(c) for c in columns)
    return f"COPY {_qualified(schema, table)} ({col_list}) FROM STDIN"  # nosec B608


def build_setval_max_sql(schema: str, table: str, col: str) -> str:
    """setval(<seq>, MAX(col)) — seq is passed as a bound %s parameter by the caller."""
    return f'SELECT setval(%s, COALESCE((SELECT MAX({_quote_ident(col)}) FROM {_qualified(schema, table)}), 1))'  # nosec B608


def server_version(conn) -> str:
    with conn.cursor() as cur:
        cur.execute("SHOW server_version")
        return cur.fetchone()[0]


def ensure_schema(conn, schema: str) -> None:
    with conn.cursor() as cur:
        cur.execute(build_create_schema_sql(schema))
    conn.commit()


def apply_sql(conn, sql: str) -> Tuple[bool, Optional[str]]:
    """Apply a SQL script in its own transaction.

    Returns (ok, error_message). Rolls back the unit on any error so a failed
    apply never leaves a half-applied object.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        return True, None
    except Exception as exc:  # noqa: BLE001 - report any DB error to caller
        conn.rollback()
        return False, str(exc).strip()


def row_count(conn, schema: str, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(build_row_count_sql(schema, table))
        return int(cur.fetchone()[0])


def primary_key_columns(conn, schema: str, table: str) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass AND i.indisprimary
            ORDER BY array_position(i.indkey, a.attnum)
            """,
            (f'"{schema}"."{table}"',),
        )
        return [r[0] for r in cur.fetchall()]


def truncate(conn, schema: str, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute(build_truncate_sql(schema, table))
    conn.commit()


def copy_rows(conn, schema: str, table: str, columns: Sequence[str],
              rows: Iterable[Sequence[Any]]) -> int:
    """Bulk-load rows via the COPY protocol. Returns the number of rows written.

    The caller is responsible for transaction commit/rollback so multiple COPY
    chunks can share a transaction if desired. Here we commit per call.
    """
    copy_sql = build_copy_sql(schema, table, columns)
    written = 0
    with conn.cursor() as cur:
        with cur.copy(copy_sql) as copy:
            for row in rows:
                copy.write_row(row)
                written += 1
    conn.commit()
    return written


# ---- adapter -------------------------------------------------------------

from .. import connections as _connections  # noqa: E402
from .base import TargetEngine  # noqa: E402


class PostgreSQLEngine(TargetEngine):
    """PostgreSQL / Aurora PostgreSQL target adapter (psycopg v3)."""

    def connect(self):
        return _connections.db_connect(self.model)

    def ping_sql(self) -> str:
        return "SELECT 1"

    def server_version(self) -> str:
        return server_version(self.connection)

    def ensure_schema(self, schema):
        ensure_schema(self.connection, schema)

    def _apply_sql(self, sql):
        return apply_sql(self.connection, sql)

    def bulk_insert(self, schema, table, columns, rows):
        return copy_rows(self.connection, schema, table, columns, rows)

    def table_exists(self, schema, table):
        with self.connection.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = %s AND table_name = %s", (schema, table))
            return cur.fetchone()[0] > 0

    def get_row_count(self, schema, table):
        return row_count(self.connection, schema, table)

    def truncate(self, schema, table):
        truncate(self.connection, schema, table)

    def primary_key_columns(self, schema, table):
        return primary_key_columns(self.connection, schema, table)

    def reset_identity(self, schema, table):
        # Advance each IDENTITY column's sequence to MAX(col) so app inserts after
        # a data load (which supplied explicit ids) don't collide.
        conn = self.connection
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s AND is_identity = 'YES'",
                (schema, table))
            cols = [r[0] for r in cur.fetchall()]
            for c in cols:
                cur.execute("SELECT pg_get_serial_sequence(%s, %s)",
                            (f"{schema}.{table}", c))
                row = cur.fetchone()
                seq = row[0] if row else None
                if seq:
                    cur.execute(build_setval_max_sql(schema, table, c), (seq,))
        conn.commit()
