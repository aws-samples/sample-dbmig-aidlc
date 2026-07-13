"""SQL Server source adapter (python-tds / pytds).

SQL Server has no ``DBMS_METADATA``-style DDL generator, so this adapter
reconstructs an object-unit's DDL from the system catalogs
(``INFORMATION_SCHEMA`` + ``sys.*``): a CREATE TABLE from column metadata plus
PK/UNIQUE/FK/CHECK constraints, secondary indexes, and triggers. Code objects
(procedures, functions, views) come from ``sys.sql_modules`` / ``OBJECT_DEFINITION``.

The reconstructed DDL is *context for the LLM (Kiro)* to convert — it reflects the
source faithfully but is not required to be byte-for-byte the original script.

String literals are inlined (single quotes doubled) to stay driver-paramstyle
agnostic; identifiers are bracket-quoted.
"""
from __future__ import annotations

from numbers import Number
from typing import Any, Dict, List, Optional, Tuple

from .. import connections as _connections
from . import _common
from .base import CodeObject, ObjectUnit, SourceEngine, assert_identifier


def _lit(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def _q(ident: str) -> str:
    return "[" + str(ident).replace("]", "]]") + "]"


# Types whose binary wire representation is unusable by a generic COPY: extract a
# portable text form at read time so the value lands in a target text column.
#   hierarchyid       -> the '/1/2/' path string  (col.ToString())
#   geography/geometry-> WKT, e.g. 'POINT (...)'   (col.STAsText())
_READ_EXPR_TEMPLATES = {
    "hierarchyid": "{col}.ToString()",
    "geography": "{col}.STAsText()",
    "geometry": "{col}.STAsText()",
}


def read_expr_template(type_name: str):
    """Return a ``{col}``-templated source read expression for a SQL Server type
    that needs read-time conversion (hierarchyid/geography/geometry), or None."""
    return _READ_EXPR_TEMPLATES.get((type_name or "").strip().lower())


def _select_term(col: str, type_name: str) -> str:
    """Build one SELECT-list term for a column: a converting expression aliased
    back to the column name when the type needs it, else the plain quoted column."""
    tmpl = read_expr_template(type_name)
    if tmpl:
        return f"{tmpl.format(col=_q(col))} AS {_q(col)}"
    return _q(col)


def _select_list(typed_cols) -> str:
    """SELECT list from [(name, type), ...], applying read-time conversions."""
    return ", ".join(_select_term(c, t) for c, t in typed_cols) or "*"


def _coltype(dt: str, charlen, prec, scale) -> str:
    d = (dt or "").lower()
    if d in ("varchar", "nvarchar", "char", "nchar", "varbinary", "binary"):
        if charlen in (-1, None):
            return f"{d}(max)" if d.startswith(("var", "n")) else d
        return f"{d}({charlen})"
    if d in ("decimal", "numeric"):
        if prec is not None:
            return f"{d}({prec},{scale or 0})"
        return d
    if d in ("datetime2", "time", "datetimeoffset") and prec is not None:
        return f"{d}({prec})"
    return d


def summarize_cross_schema_deps(rows, schema: str) -> List[Dict[str, Any]]:
    """Re-exported from engines._common (shared with the Oracle adapter)."""
    return _common.summarize_cross_schema_deps(rows, schema)


class SQLServerEngine(SourceEngine):
    """Microsoft SQL Server source adapter."""

    def connect(self):
        return _connections.db_connect(self.model)

    def ping_sql(self) -> str:
        return "SELECT 1"

    def server_version(self) -> str:
        v = self.scalar("SELECT @@VERSION")
        return str(v).splitlines()[0].strip() if v else "unknown"

    # ---- inventory / listings --------------------------------------------
    def list_tables(self, schema: str, only: Optional[List[str]] = None) -> List[str]:
        assert_identifier(schema)
        _, rows = self.fetch(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "  # nosec B608
            f"WHERE TABLE_SCHEMA = {_lit(schema)} AND TABLE_TYPE = 'BASE TABLE' "
            "ORDER BY TABLE_NAME")
        names = [r[0] for r in rows]
        if only:
            wanted = {t.upper() for t in only}
            names = [n for n in names if n.upper() in wanted]
        return names

    def table_columns(self, schema: str, table: str) -> List[Tuple[str, str]]:
        assert_identifier(schema, table)
        _, rows = self.fetch(
            "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "  # nosec B608
            f"WHERE TABLE_SCHEMA = {_lit(schema)} AND TABLE_NAME = {_lit(table)} "
            "ORDER BY ORDINAL_POSITION")
        return [(r[0], r[1]) for r in rows]

    def primary_key_columns(self, schema: str, table: str) -> List[str]:
        assert_identifier(schema, table)
        _, rows = self.fetch(
            "SELECT kcu.COLUMN_NAME "  # nosec B608
            "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc "
            "JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu "
            "  ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME "
            " AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA "
            f"WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY' "
            f"  AND tc.TABLE_SCHEMA = {_lit(schema)} AND tc.TABLE_NAME = {_lit(table)} "
            "ORDER BY kcu.ORDINAL_POSITION")
        return [r[0] for r in rows]

    def _row_count_estimate(self, schema: str, table: str) -> int:
        v = self.scalar(
            "SELECT SUM(p.rows) FROM sys.partitions p "  # nosec B608
            "JOIN sys.tables t ON p.object_id = t.object_id "
            "JOIN sys.schemas s ON t.schema_id = s.schema_id "
            f"WHERE s.name = {_lit(schema)} AND t.name = {_lit(table)} "
            "AND p.index_id IN (0,1)")
        return int(v) if v is not None else -1

    # ---- DDL reconstruction ----------------------------------------------
    def _computed_columns(self, schema: str, table: str) -> Dict[str, str]:
        """Map of computed-column name -> its SQL Server definition. These appear
        in INFORMATION_SCHEMA.COLUMNS as ordinary columns (no expression), so we
        annotate them for the converter (migrate as a stored value, or convert to
        a PostgreSQL GENERATED column)."""
        oid = f"OBJECT_ID({_lit(schema + '.' + table)})"
        try:
            _, rows = self.fetch(
                f"SELECT name, definition FROM sys.computed_columns WHERE object_id = {oid}")  # nosec B608
            return {r[0]: (r[1] or "").strip() for r in rows}
        except Exception:
            return {}

    def _table_ddl(self, schema: str, table: str) -> str:
        _, rows = self.fetch(
            "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, "  # nosec B608
            "NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE, COLUMN_DEFAULT, "
            f"COLUMNPROPERTY(OBJECT_ID({_lit(schema + '.' + table)}), COLUMN_NAME, 'IsIdentity') "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            f"WHERE TABLE_SCHEMA = {_lit(schema)} AND TABLE_NAME = {_lit(table)} "
            "ORDER BY ORDINAL_POSITION")
        cols = []
        computed = self._computed_columns(schema, table)
        for name, dt, clen, prec, scale, nullable, default, is_identity in rows:
            parts = [f"    {_q(name)} {_coltype(dt, clen, prec, scale)}"]
            if is_identity:
                parts.append("IDENTITY(1,1)")
            if (nullable or "").upper() == "NO":
                parts.append("NOT NULL")
            if default is not None:
                parts.append(f"DEFAULT {default}")
            line = " ".join(parts)
            if name in computed:
                # Computed in source — flag so the converter chooses a stored
                # value (migrate the computed result) or a GENERATED column.
                line = f"    -- computed in source: {computed[name]}\n" + line
            cols.append(line)
        body = ",\n".join(cols)
        return f"CREATE TABLE {_q(schema)}.{_q(table)} (\n{body}\n);"

    def _constraints_ddl(self, schema: str, table: str) -> str:
        oid = f"OBJECT_ID({_lit(schema + '.' + table)})"
        out = []
        # PK / UNIQUE
        _, rows = self.fetch(
            "SELECT tc.CONSTRAINT_NAME, tc.CONSTRAINT_TYPE, "  # nosec B608
            "(SELECT STRING_AGG(QUOTENAME(kcu.COLUMN_NAME), ', ') "
            "   WITHIN GROUP (ORDER BY kcu.ORDINAL_POSITION) "
            " FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu "
            " WHERE kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME "
            "   AND kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA) AS cols "
            "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc "
            f"WHERE tc.TABLE_SCHEMA = {_lit(schema)} AND tc.TABLE_NAME = {_lit(table)} "
            "AND tc.CONSTRAINT_TYPE IN ('PRIMARY KEY','UNIQUE')")
        for cname, ctype, cols in rows:
            if cols:
                out.append(f"ALTER TABLE {_q(schema)}.{_q(table)} ADD CONSTRAINT "
                           f"{_q(cname)} {ctype} ({cols});")
        # CHECK
        _, rows = self.fetch(
            f"SELECT name, definition FROM sys.check_constraints WHERE parent_object_id = {oid}")  # nosec B608
        for cname, definition in rows:
            out.append(f"ALTER TABLE {_q(schema)}.{_q(table)} ADD CONSTRAINT "
                       f"{_q(cname)} CHECK {definition};")
        return "\n".join(out)

    def _foreign_keys_ddl(self, schema: str, table: str) -> str:
        oid = f"OBJECT_ID({_lit(schema + '.' + table)})"
        _, rows = self.fetch(
            "SELECT fk.name, "  # nosec B608
            " STRING_AGG(QUOTENAME(COL_NAME(fkc.parent_object_id, fkc.parent_column_id)), ', ') "
            "   WITHIN GROUP (ORDER BY fkc.constraint_column_id) AS cols, "
            " OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS ref_schema, "
            " OBJECT_NAME(fk.referenced_object_id) AS ref_name, "
            " STRING_AGG(QUOTENAME(COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id)), ', ') "
            "   WITHIN GROUP (ORDER BY fkc.constraint_column_id) AS ref_cols "
            "FROM sys.foreign_keys fk "
            "JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id "
            f"WHERE fk.parent_object_id = {oid} "
            "GROUP BY fk.name, fk.referenced_object_id")
        out = []
        for name, cols, ref_schema, ref_name, ref_cols in rows:
            ref_table = f"{_q(ref_schema)}.{_q(ref_name)}"
            out.append(f"ALTER TABLE {_q(schema)}.{_q(table)} ADD CONSTRAINT "
                       f"{_q(name)} FOREIGN KEY ({cols}) REFERENCES {ref_table} ({ref_cols});")
        return "\n".join(out)

    def _indexes_ddl(self, schema: str, table: str) -> str:
        oid = f"OBJECT_ID({_lit(schema + '.' + table)})"
        _, rows = self.fetch(
            "SELECT i.name, i.is_unique, i.type_desc, "  # nosec B608
            " STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS cols "
            "FROM sys.indexes i "
            "JOIN sys.index_columns ic ON i.object_id = ic.object_id "
            " AND i.index_id = ic.index_id AND ic.is_included_column = 0 "
            "JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id "
            f"WHERE i.object_id = {oid} AND i.is_primary_key = 0 "
            "AND i.is_unique_constraint = 0 AND i.type IN (1,2) AND i.name IS NOT NULL "
            "GROUP BY i.name, i.is_unique, i.type_desc")
        out = []
        for name, is_unique, type_desc, cols in rows:
            uniq = "UNIQUE " if is_unique else ""
            out.append(f"-- {type_desc}\nCREATE {uniq}INDEX {_q(name)} "
                       f"ON {_q(schema)}.{_q(table)} ({cols});")
        return "\n".join(out)

    def _triggers_ddl(self, schema: str, table: str) -> str:
        oid = f"OBJECT_ID({_lit(schema + '.' + table)})"
        _, rows = self.fetch(
            "SELECT m.definition FROM sys.triggers t "  # nosec B608
            "JOIN sys.sql_modules m ON t.object_id = m.object_id "
            f"WHERE t.parent_id = {oid}")
        return "\n\n".join((r[0] or "").strip() for r in rows if r[0])

    def extract_object_unit(self, schema: str, table: str) -> ObjectUnit:
        assert_identifier(schema, table)
        components = {
            "table": self._table_ddl(schema, table),
            "constraints": self._constraints_ddl(schema, table),
            "ref_constraints": self._foreign_keys_ddl(schema, table),
            "indexes": self._indexes_ddl(schema, table),
            "triggers": self._triggers_ddl(schema, table),
            "comments": "",
            "grants": "",
        }
        return ObjectUnit(schema=schema, name=table, components=components,
                          num_rows=self._row_count_estimate(schema, table))

    # ---- code objects -----------------------------------------------------
    _TYPE_DESC = {"P": "PROCEDURE", "FN": "FUNCTION", "IF": "FUNCTION",
                  "TF": "FUNCTION", "V": "VIEW"}

    def list_callables(self, schema: str) -> List[Tuple[str, str]]:
        _, rows = self.fetch(
            "SELECT o.type, o.name FROM sys.objects o "  # nosec B608
            "JOIN sys.schemas s ON o.schema_id = s.schema_id "
            f"WHERE s.name = {_lit(schema)} AND o.type IN ('P','FN','IF','TF','V') "
            "ORDER BY o.type, o.name")
        return [(self._TYPE_DESC.get(t.strip(), t.strip()), n) for t, n in rows]

    def code_object_ddl(self, schema: str, object_type: str, name: str) -> str:
        assert_identifier(schema, name)
        v = self.scalar(f"SELECT OBJECT_DEFINITION(OBJECT_ID({_lit(schema + '.' + name)}))")
        return (v or "").strip()

    def extract_code_objects(self, schema: str) -> List[CodeObject]:
        _, rows = self.fetch(
            "SELECT o.type, o.name, m.definition FROM sys.sql_modules m "  # nosec B608
            "JOIN sys.objects o ON m.object_id = o.object_id "
            "JOIN sys.schemas s ON o.schema_id = s.schema_id "
            f"WHERE s.name = {_lit(schema)} AND o.type IN ('P','FN','IF','TF','V') "
            "ORDER BY o.type, o.name")
        out = []
        for t, name, definition in rows:
            if (definition or "").strip():
                out.append(CodeObject(schema, self._TYPE_DESC.get(t.strip(), t.strip()),
                                      name, definition.strip()))
        return out

    # ---- sampling / chunking ---------------------------------------------
    def sample_rows(self, schema: str, table: str, n: int = 5):
        assert_identifier(schema, table)
        try:
            cols, rows = self.fetch(
                f"SELECT TOP {int(n)} * FROM {_q(schema)}.{_q(table)}")  # nosec B608
            return cols, rows
        except Exception:
            return [], []

    def chunk_iterator(self, schema, table, pk_cols, batch_size):
        assert_identifier(schema, table, *pk_cols)
        typed = self.table_columns(schema, table)
        # Convert hierarchyid/geography/geometry to portable text at read time so
        # a generic COPY into a target text column works (no opaque binary).
        col_list = _select_list(typed)
        base = f"SELECT {col_list} FROM {_q(schema)}.{_q(table)}"  # nosec B608
        if len(pk_cols) == 1:
            pk = pk_cols[0]
            lo = self.scalar(f"SELECT MIN({_q(pk)}) FROM {_q(schema)}.{_q(table)}")  # nosec B608
            hi = self.scalar(f"SELECT MAX({_q(pk)}) FROM {_q(schema)}.{_q(table)}")  # nosec B608
            if isinstance(lo, Number) and isinstance(hi, Number) and hi >= lo:
                lo_i, hi_i = int(lo), int(hi)
                step = max(1, int(batch_size))
                cur = lo_i
                while cur <= hi_i:
                    yield (f"{base} WHERE {_q(pk)} >= {cur} AND {_q(pk)} < {cur + step} "
                           f"ORDER BY {_q(pk)}", {})
                    cur += step
                return
        yield (base, {})

    # ---- aggregate / inventory -------------------------------------------
    def count_rows(self, schema: str, table: str) -> int:
        assert_identifier(schema, table)
        return int(self.scalar(f"SELECT COUNT(*) FROM {_q(schema)}.{_q(table)}") or 0)  # nosec B608

    def foreign_key_deps(self, schema: str, tables):
        up = {t.upper() for t in tables}
        deps = {t: set() for t in up}
        _, rows = self.fetch(
            "SELECT OBJECT_NAME(fk.parent_object_id), "  # nosec B608
            "       OBJECT_SCHEMA_NAME(fk.referenced_object_id), "
            "       OBJECT_NAME(fk.referenced_object_id) "
            "FROM sys.foreign_keys fk "
            "JOIN sys.objects o ON fk.parent_object_id = o.object_id "
            "JOIN sys.schemas s ON o.schema_id = s.schema_id "
            f"WHERE s.name = {_lit(schema)}")
        for child, ref_schema, parent in rows:
            # Only FKs whose referenced table is in the SAME schema affect this
            # schema's load ordering. Without the schema check, a parent in another
            # schema that happens to share a name with an in-scope table would be
            # wrongly treated as in-scope and distort the topological order.
            if (ref_schema or "").upper() != schema.upper():
                continue
            c, p = (child or "").upper(), (parent or "").upper()
            if c in up and p in up and c != p:
                deps[c].add(p)
        return deps

    def get_table_list(self, schema: str) -> List[Dict[str, Any]]:
        out = []
        for name in self.list_tables(schema):
            out.append({"name": name,
                        "row_count": self._row_count_estimate(schema, name),
                        "columns": len(self.table_columns(schema, name))})
        return out

    def cross_schema_dependencies(self, schema: str) -> List[Dict[str, Any]]:
        """Objects in ``schema`` that reference objects in OTHER schemas, grouped by the
        referenced schema (via sys.sql_expression_dependencies). Useful for partial
        migrations: it flags up front what a schema depends on outside its own boundary."""
        assert_identifier(schema)
        try:
            _, rows = self.fetch(
                "SELECT OBJECT_NAME(d.referencing_id) AS obj, "  # nosec B608
                "       rs.name AS ref_schema, ro.name AS ref_obj "
                "FROM sys.sql_expression_dependencies d "
                "JOIN sys.objects o ON o.object_id = d.referencing_id "
                "JOIN sys.schemas s ON s.schema_id = o.schema_id "
                "LEFT JOIN sys.objects ro ON ro.object_id = d.referenced_id "
                "LEFT JOIN sys.schemas rs ON rs.schema_id = ro.schema_id "
                f"WHERE s.name = {_lit(schema)} "
                "AND rs.name IS NOT NULL AND rs.name <> s.name")
        except Exception:
            return []
        return summarize_cross_schema_deps([(r[0], r[1], r[2]) for r in rows], schema)

    def inventory(self, schema: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {"schema": schema}
        _, rows = self.fetch(
            "SELECT o.type_desc, COUNT(*) FROM sys.objects o "  # nosec B608
            "JOIN sys.schemas s ON o.schema_id = s.schema_id "
            f"WHERE s.name = {_lit(schema)} "
            "AND o.type IN ('U','V','P','FN','IF','TF','TR') "
            "GROUP BY o.type_desc ORDER BY o.type_desc")
        result["object_counts"] = {r[0]: int(r[1]) for r in rows}
        result["tables"] = self.get_table_list(schema)
        _, rows = self.fetch(
            "SELECT DATA_TYPE, COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "  # nosec B608
            f"WHERE TABLE_SCHEMA = {_lit(schema)} GROUP BY DATA_TYPE ORDER BY COUNT(*) DESC")
        result["datatypes"] = {r[0]: int(r[1]) for r in rows}
        result["code_units"] = [
            {"type": t, "name": n} for t, n in self.list_callables(schema)]
        result["cross_schema_dependencies"] = self.cross_schema_dependencies(schema)
        return result
