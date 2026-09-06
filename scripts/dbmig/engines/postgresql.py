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


# ---- FDW push-down builders ----------------------------------------------
# These build the DDL for the ``migrate-data --method fdw`` path: the target
# PostgreSQL reads directly from the source through a foreign data wrapper
# (oracle_fdw / tds_fdw), so bulk data moves source->target server-side and the
# toolkit only issues control SQL. Identifiers are quoted; OPTION *values*
# (including the source password) are escaped as SQL string literals. OPTION keys
# and the wrapper/extension name come only from trusted engine code but are
# validated defensively against a strict allowlist.

import re as _re  # noqa: E402

_FDW_NAME_RE = _re.compile(r"^[a-z_][a-z0-9_]*$")


def _assert_fdw_name(name: str) -> None:
    """Validate an unquoted SQL name used verbatim (extension / option key)."""
    if not name or not _FDW_NAME_RE.match(name):
        raise ValueError(f"unsafe FDW identifier: {name!r}")


def _fdw_opt_literal(value) -> str:
    """A single-quoted SQL string literal for an FDW OPTION value (doubling quotes)."""
    return "'" + str(value).replace("'", "''") + "'"


def _fdw_options_clause(options) -> str:
    parts = []
    for k, v in options.items():
        _assert_fdw_name(str(k))
        parts.append(f"{k} {_fdw_opt_literal(v)}")
    return ", ".join(parts)


def build_create_extension_sql(wrapper: str) -> str:
    _assert_fdw_name(wrapper)
    return f"CREATE EXTENSION IF NOT EXISTS {wrapper}"  # nosec B608


def build_create_server_sql(server: str, wrapper: str, options) -> str:
    _assert_fdw_name(wrapper)
    return (f"CREATE SERVER {_quote_ident(server)} "  # nosec B608
            f"FOREIGN DATA WRAPPER {wrapper} OPTIONS ({_fdw_options_clause(options)})")


def build_create_user_mapping_sql(server: str, options) -> str:
    return (f"CREATE USER MAPPING FOR CURRENT_USER "  # nosec B608
            f"SERVER {_quote_ident(server)} OPTIONS ({_fdw_options_clause(options)})")


def build_create_foreign_table_sql(stage: str, ftname: str,
                                   columns, server: str, options) -> str:
    """``columns`` is a sequence of (name, type_sql); ``type_sql`` comes from the
    target catalog's ``format_type`` (a valid, re-parseable PG type string)."""
    col_defs = ", ".join(f"{_quote_ident(n)} {t}" for n, t in columns)
    return (f"CREATE FOREIGN TABLE {_qualified(stage, ftname)} ({col_defs}) "  # nosec B608
            f"SERVER {_quote_ident(server)} OPTIONS ({_fdw_options_clause(options)})")


def build_fdw_insert_select_sql(tgt_schema: str, tgt_table: str, insert_cols,
                                stage: str, ftname: str, select_exprs,
                                pk: Optional[str] = None,
                                lo: Optional[int] = None,
                                hi: Optional[int] = None) -> str:
    """INSERT INTO <target> (insert_cols) SELECT select_exprs FROM <stage.ft> [WHERE
    pk range]. ``insert_cols`` are target column names (quoted here); ``select_exprs``
    are ready SQL expressions over the foreign table's (source-named) columns, aligned
    by position — usually the quoted column name, or a ``CAST(...)`` where the wrapper
    needs a target-side conversion. PK-range bounds are integers (from
    ``numeric_pk_bounds``) inlined as literals so the wrapper pushes the predicate down
    to the source for each shard."""
    ins = ", ".join(_quote_ident(c) for c in insert_cols)
    sel = ", ".join(select_exprs)
    sql = (f"INSERT INTO {_qualified(tgt_schema, tgt_table)} ({ins}) "  # nosec B608
           f"SELECT {sel} FROM {_qualified(stage, ftname)}")
    if pk is not None and lo is not None and hi is not None:
        sql += (f" WHERE {_quote_ident(pk)} >= {int(lo)} "
                f"AND {_quote_ident(pk)} < {int(hi)}")
    return sql


def build_fdw_delete_range_sql(schema: str, table: str, pk: str,
                               lo: int, hi: int) -> str:
    return (f"DELETE FROM {_qualified(schema, table)} "  # nosec B608
            f"WHERE {_quote_ident(pk)} >= {int(lo)} AND {_quote_ident(pk)} < {int(hi)}")


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

    # PostgreSQL can pull directly from Oracle/SQL Server via oracle_fdw/tds_fdw,
    # so ``migrate-data --method fdw`` is available for this target.
    fdw_capable = True

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

    # ---- FDW push-down load (target reads source directly) -----------------

    def target_column_types(self, schema, table):
        """Return [(column_name, type_sql)] for the target table in ordinal order,
        where ``type_sql`` is ``format_type`` output — a valid, re-parseable PG type
        string (e.g. ``numeric(10,2)``, ``character varying(50)``, ``demo.myenum``).
        Used to declare the FDW foreign table with the exact target column types so
        the server-side ``INSERT ... SELECT`` lands values as the converted schema
        expects. Empty if the table does not exist."""
        _, rows = self.fetch(
            "SELECT a.attname, format_type(a.atttypid, a.atttypmod) "
            "FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = %s AND c.relname = %s "
            "AND a.attnum > 0 AND NOT a.attisdropped "
            "ORDER BY a.attnum", (schema, table))
        return [(str(r[0]), str(r[1])) for r in rows]

    def fdw_setup_server(self, wrapper, server, server_options, user_mapping_options):
        """Create the extension (if needed), (re)create the foreign server and the
        current user's user mapping. Drops any pre-existing server of the same name
        first so a re-run refreshes the options cleanly."""
        conn = self.connection
        with conn.cursor() as cur:
            cur.execute(build_create_extension_sql(wrapper))
            cur.execute(f"DROP SERVER IF EXISTS {_quote_ident(server)} CASCADE")  # nosec B608
            cur.execute(build_create_server_sql(server, wrapper, server_options))
            cur.execute(build_create_user_mapping_sql(server, user_mapping_options))
        conn.commit()

    def fdw_create_stage_schema(self, stage):
        with self.connection.cursor() as cur:
            cur.execute(build_create_schema_sql(stage))
        self.connection.commit()

    def fdw_create_foreign_table(self, stage, ftname, columns, server, options):
        conn = self.connection
        with conn.cursor() as cur:
            cur.execute(f"DROP FOREIGN TABLE IF EXISTS {_qualified(stage, ftname)}")  # nosec B608
            cur.execute(build_create_foreign_table_sql(stage, ftname, columns,
                                                       server, options))
        conn.commit()

    def fdw_insert_select(self, tgt_schema, tgt_table, insert_cols, stage, ftname,
                          select_exprs, pk=None, lo=None, hi=None):
        """Run the server-side INSERT ... SELECT from the foreign table into the
        target and return the number of rows inserted."""
        sql = build_fdw_insert_select_sql(tgt_schema, tgt_table, insert_cols,
                                          stage, ftname, select_exprs, pk, lo, hi)
        conn = self.connection
        with conn.cursor() as cur:
            cur.execute(sql)
            n = cur.rowcount
        conn.commit()
        return int(n if n is not None and n >= 0 else 0)

    def fdw_delete_range(self, schema, table, pk, lo, hi):
        conn = self.connection
        with conn.cursor() as cur:
            cur.execute(build_fdw_delete_range_sql(schema, table, pk, lo, hi))
        conn.commit()

    def fdw_cleanup(self, server, stage):
        """Remove the FDW objects created for a load: the server (CASCADE, which
        drops the user mapping and all foreign tables) and the staging schema. This
        also removes the source credentials stored in the user mapping."""
        conn = self.connection
        with conn.cursor() as cur:
            cur.execute(f"DROP SERVER IF EXISTS {_quote_ident(server)} CASCADE")  # nosec B608
            if stage:
                cur.execute(f"DROP SCHEMA IF EXISTS {_quote_ident(stage)} CASCADE")  # nosec B608
        conn.commit()

    # ---- live target introspection (for diff-target / capture) --------------

    def live_schema_catalog(self, schema: str) -> dict:
        """Return the set of object names that currently exist in ``schema`` on the
        live target, grouped by kind. Names are lower-cased for matching against
        the (lower-case) DMS SC target names.

        Kinds: tables, views, sequences, indexes, constraints, triggers, routines.
        One batch of catalog queries so callers can diff many objects cheaply.
        """
        q = {
            "tables": ("SELECT table_name FROM information_schema.tables "
                       "WHERE table_schema=%s AND table_type='BASE TABLE'"),
            "views": ("SELECT table_name FROM information_schema.views "
                      "WHERE table_schema=%s"),
            "sequences": ("SELECT sequence_name FROM information_schema.sequences "
                          "WHERE sequence_schema=%s"),
            "indexes": "SELECT indexname FROM pg_indexes WHERE schemaname=%s",
            "constraints": ("SELECT constraint_name FROM information_schema.table_constraints "
                            "WHERE constraint_schema=%s"),
            "triggers": ("SELECT DISTINCT trigger_name FROM information_schema.triggers "
                         "WHERE trigger_schema=%s"),
            "routines": ("SELECT p.proname FROM pg_proc p JOIN pg_namespace n "
                         "ON n.oid=p.pronamespace WHERE n.nspname=%s"),
        }
        out: dict = {}
        for kind, sql in q.items():
            _, rows = self.fetch(sql, (schema,))
            out[kind] = {str(r[0]).lower() for r in rows}
        return out

    def routine_definitions(self, schema: str) -> dict:
        """name (lower) -> normalized concatenation of pg_get_functiondef for all
        overloads with that name. Used for definition-level diffing of code."""
        out: dict = {}
        _, rows = self.fetch(
            "SELECT p.proname, pg_get_functiondef(p.oid) "
            "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
            "WHERE n.nspname=%s AND p.prokind IN ('f','p')", (schema,))
        for name, ddl in rows:
            out.setdefault(str(name).lower(), []).append(ddl or "")
        return {k: "\n".join(v) for k, v in out.items()}

    def view_definitions(self, schema: str) -> dict:
        """view name (lower) -> definition SQL."""
        _, rows = self.fetch(
            "SELECT viewname, definition FROM pg_views WHERE schemaname=%s", (schema,))
        return {str(n).lower(): (d or "") for n, d in rows}

    def capture_secondary_objects(self, schema: str) -> dict:
        """Capture the load-hostile *secondary* objects that should be dropped before a
        bulk data load and recreated after: foreign keys, NON-UNIQUE secondary indexes,
        and triggers. Primary keys and UNIQUE constraints/indexes are deliberately kept
        (the PK-chunked, resumable data copy relies on the PK, and unique keys are cheap
        and risky to re-add against loaded data).

        Returns {"foreign_keys": [...], "indexes": [...], "triggers": [...]} where each
        item is {name, table, create_sql, drop_sql} with DDL captured from the LIVE
        target (so it reflects reality, including any hand edits).
        """
        sch = _quote_ident(schema)

        # Foreign keys ------------------------------------------------------
        _, fk_rows = self.fetch(
            "SELECT con.conname, rel.relname, pg_get_constraintdef(con.oid) "
            "FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_namespace n ON n.oid = con.connamespace "
            "WHERE n.nspname = %s AND con.contype = 'f' "
            "ORDER BY rel.relname, con.conname", (schema,))
        fks = [{
            "name": name, "table": tbl,
            "create_sql": f"ALTER TABLE {sch}.{_quote_ident(tbl)} "
                          f"ADD CONSTRAINT {_quote_ident(name)} {cdef};",
            "drop_sql": f"ALTER TABLE {sch}.{_quote_ident(tbl)} "
                        f"DROP CONSTRAINT IF EXISTS {_quote_ident(name)};",
        } for name, tbl, cdef in fk_rows]

        # Non-unique secondary indexes (pg_indexes.indexdef starts with
        # 'CREATE INDEX'; 'CREATE UNIQUE INDEX' and PK/unique-backing indexes are
        # skipped so PK/unique enforcement is preserved). ---------------------
        _, idx_rows = self.fetch(
            "SELECT indexname, tablename, indexdef FROM pg_indexes "
            "WHERE schemaname = %s AND indexdef ILIKE 'CREATE INDEX%%' "
            "ORDER BY tablename, indexname", (schema,))
        indexes = [{
            "name": name, "table": tbl,
            "create_sql": (idef if idef.rstrip().endswith(";") else idef + ";"),
            "drop_sql": f"DROP INDEX IF EXISTS {sch}.{_quote_ident(name)};",
        } for name, tbl, idef in idx_rows]

        # Triggers (skip internal/constraint triggers) ----------------------
        _, trg_rows = self.fetch(
            "SELECT t.tgname, c.relname, pg_get_triggerdef(t.oid) "
            "FROM pg_trigger t "
            "JOIN pg_class c ON c.oid = t.tgrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = %s AND NOT t.tgisinternal "
            "ORDER BY c.relname, t.tgname", (schema,))
        triggers = [{
            "name": name, "table": tbl,
            "create_sql": (tdef if tdef.rstrip().endswith(";") else tdef + ";"),
            "drop_sql": f"DROP TRIGGER IF EXISTS {_quote_ident(name)} "
                        f"ON {sch}.{_quote_ident(tbl)};",
        } for name, tbl, tdef in trg_rows]

        return {"foreign_keys": fks, "indexes": indexes, "triggers": triggers}
