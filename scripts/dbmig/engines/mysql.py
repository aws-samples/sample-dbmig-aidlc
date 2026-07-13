"""MySQL / Aurora MySQL target helpers: apply DDL, bulk insert, counts.

Mirrors the function interface of ``engines/postgresql.py`` so the commands can
dispatch to either target engine. Uses an open ``pymysql`` connection.

Note: in MySQL a *schema* is a *database*. The Oracle source schema name (folded
to lower case) maps to a MySQL database; objects are referenced fully-qualified
with backtick-quoted identifiers (database.table).
"""
from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence, Tuple


# ---- safe SQL construction ------------------------------------------------
# Identifiers (database/table/column) cannot be passed as bound query
# parameters, so they are backtick-quoted here before interpolation. These
# builders centralize that quoting and return a finished SQL string; callers
# pass the returned string to the driver, and all *data values* are passed as
# bound parameters (never formatted). See SECURITY.md ("SQL construction").

def _quote_ident(name: str) -> str:
    """Backtick-quote a MySQL identifier, doubling any embedded backticks."""
    return "`" + str(name).replace("`", "``") + "`"


def _qualified(schema: str, table: str) -> str:
    return f"{_quote_ident(schema)}.{_quote_ident(table)}"


def build_create_database_sql(schema: str) -> str:
    return f"CREATE DATABASE IF NOT EXISTS {_quote_ident(schema)}"  # nosec B608


def build_row_count_sql(schema: str, table: str) -> str:
    return f"SELECT COUNT(*) FROM {_qualified(schema, table)}"  # nosec B608


def build_truncate_sql(schema: str, table: str) -> str:
    return f"TRUNCATE TABLE {_qualified(schema, table)}"  # nosec B608


def build_insert_sql(schema: str, table: str, columns: Sequence[str]) -> str:
    """Build a parameterized INSERT: identifiers quoted, values are %s binds."""
    col_list = ", ".join(_quote_ident(c) for c in columns)
    placeholders = ", ".join(["%s"] * len(list(columns)))
    return f"INSERT INTO {_qualified(schema, table)} ({col_list}) VALUES ({placeholders})"  # nosec B608


def build_max_plus_one_sql(schema: str, table: str, col: str) -> str:
    return f"SELECT COALESCE(MAX({_quote_ident(col)}), 0) + 1 FROM {_qualified(schema, table)}"  # nosec B608


def build_set_auto_increment_sql(schema: str, table: str, nxt: int) -> str:
    return f"ALTER TABLE {_qualified(schema, table)} AUTO_INCREMENT = {int(nxt)}"  # nosec B608


def server_version(conn) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT VERSION()")
        return cur.fetchone()[0]


def ensure_schema(conn, schema: str) -> None:
    """A MySQL 'schema' is a database — create it if missing."""
    with conn.cursor() as cur:
        cur.execute(build_create_database_sql(schema))
    conn.commit()


def apply_sql(conn, sql: str) -> Tuple[bool, Optional[str]]:
    """Apply a SQL script in its own transaction (DDL auto-commits in MySQL).

    A unit may contain several statements (the connection enables MULTI_STATEMENTS),
    so drain any extra result sets before returning to avoid 'commands out of sync'
    on the next operation.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            while cur.nextset():
                pass
        conn.commit()
        return True, None
    except Exception as exc:  # noqa: BLE001
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(exc).strip()


def row_count(conn, schema: str, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(build_row_count_sql(schema, table))
        return int(cur.fetchone()[0])


def primary_key_columns(conn, schema: str, table: str) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT k.column_name
            FROM information_schema.table_constraints t
            JOIN information_schema.key_column_usage k
              ON t.constraint_name = k.constraint_name
             AND t.table_schema = k.table_schema
             AND t.table_name = k.table_name
            WHERE t.constraint_type = 'PRIMARY KEY'
              AND t.table_schema = %s AND t.table_name = %s
            ORDER BY k.ordinal_position
            """,
            (schema, table),
        )
        return [r[0] for r in cur.fetchall()]


def truncate(conn, schema: str, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute(build_truncate_sql(schema, table))
    conn.commit()


def copy_rows(conn, schema: str, table: str, columns: Sequence[str],
              rows: Iterable[Sequence[Any]]) -> int:
    """Bulk-load rows via batched executemany INSERT (MySQL has no COPY).

    Streams from the ``rows`` iterable in batches via ``itertools.islice`` so a
    large source chunk is never fully materialized. Returns rows written.
    """
    import itertools

    cols = list(columns)
    if not cols:
        return 0
    sql = build_insert_sql(schema, table, cols)
    written = 0
    batch = 1000
    it = iter(rows)
    with conn.cursor() as cur:
        while True:
            chunk = [tuple(r) for r in itertools.islice(it, batch)]
            if not chunk:
                break
            cur.executemany(sql, chunk)
            written += len(chunk)
    conn.commit()
    return written


# ---- adapter -------------------------------------------------------------

from .. import connections as _connections  # noqa: E402
from .base import TargetEngine  # noqa: E402


class MySQLEngine(TargetEngine):
    """MySQL / Aurora MySQL target adapter (pymysql)."""

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

    def get_row_count(self, schema, table):
        return row_count(self.connection, schema, table)

    def truncate(self, schema, table):
        truncate(self.connection, schema, table)

    def primary_key_columns(self, schema, table):
        return primary_key_columns(self.connection, schema, table)

    def reset_identity(self, schema, table):
        # Set AUTO_INCREMENT to MAX(col)+1 after a data load.
        conn = self.connection
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s "
                "AND extra LIKE '%%auto_increment%%'", (schema, table))
            row = cur.fetchone()
            if not row:
                return
            col = row[0]
            cur.execute(build_max_plus_one_sql(schema, table, col))
            nxt = cur.fetchone()[0]
            cur.execute(build_set_auto_increment_sql(schema, table, nxt))
        conn.commit()
