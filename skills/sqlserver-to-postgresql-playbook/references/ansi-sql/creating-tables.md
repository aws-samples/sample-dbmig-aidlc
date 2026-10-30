# Creating Tables (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.tables.html

**Conversion category:** Assisted (Three-star compatibility, four-star automation)
**SCT automation:** SCT action code index: Creating Tables. Key differences: auto-generated value column differs; can't use physical attribute `ON <File Group>`; no table variables or memory-optimized tables.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PG 18 virtual/stored generated columns for computed columns (verified), identity instead of SERIAL, `DBCC CHECKIDENT` → `RESTART`, `##` temp tables have no equivalent, fixed `LIKE` syntax and the recursive ROWVERSION trigger example, `xmin` concurrency token.

## SQL Server

`CREATE TABLE` is ANSI/ISO entry-level conformant. T-SQL extensions add index types (`CLUSTERED`/`NONCLUSTERED`, `FILLFACTOR`), physical storage via `ON <File Group>`, `IDENTITY` columns, encryption, compression, and indexes.

Five table scopes: standard, temporary (`#`), global temporary (`##`), table variables (`DECLARE`), memory-optimized tables.

Simplified syntax:
```sql
CREATE TABLE [<Database Name>.<Schema Name>].<Table Name> (<Column Definitions>)
  [ON{<Partition Scheme Name> (<Partition Column Name>)];
```

`SELECT INTO` (DML+DDL; copies only column names, order, and data types — no constraints/keys/indexes/identity/defaults):
```sql
SELECT <Expression List>
INTO <Table Name>
[FROM <Table Source>]
[WHERE <Filter>]
[GROUP BY <Grouping Expressions>...];
```

Examples:
```sql
-- Basic table
CREATE TABLE MyTable
(
Col1 INT NOT NULL PRIMARY KEY,
Col2 VARCHAR(20) NOT NULL
);

-- Column constraints and identity
CREATE TABLE MyTable
(
Col1 INT NOT NULL PRIMARY KEY IDENTITY (1,1),
Col2 VARCHAR(20) NOT NULL CHECK (Col2 <> ''),
Col3 VARCHAR(100) NULL
REFERENCES MyOtherTable (Col3)
);

-- Additional inline index
CREATE TABLE MyTable
(
Col1 INT NOT NULL PRIMARY KEY,
Col2 VARCHAR(20) NOT NULL
INDEX IDX_Col2 NONCLUSTERED
);
```

`TIMESTAMP`/`ROWVERSION`: deprecated synonym; neither is supported by AWS SCT for Aurora PostgreSQL. Replace with custom logic (e.g., a trigger).

## PostgreSQL

ANSI/ISO entry-level conformant `CREATE TABLE`. There is no inline `INDEX` clause in a column definition; create indexes with separate `CREATE INDEX` statements. Two table scopes: standard and temporary (`CREATE TEMPORARY TABLE`; the `GLOBAL` keyword is accepted but ignored, verified on 18.6, so a temp table is always session-private).

Generated columns, the equivalent of SQL Server **computed columns** (verified on 18.6):
```sql
CREATE TABLE tst_gen(
  n     numeric,
  n_gen numeric GENERATED ALWAYS AS (n * 0.01),          -- PG 18: VIRTUAL by default (computed on read)
  n_st  numeric GENERATED ALWAYS AS (n * 0.01) STORED     -- ≈ SQL Server PERSISTED computed column
);
```
SQL Server computed column → `VIRTUAL`; `PERSISTED` computed column, or any computed column that is indexed, unique, an FK target, or uses a user-defined function → `STORED`. PG 18 virtual columns cannot be indexed and cannot call user-defined functions (both verified). Every function used must be `IMMUTABLE`, so `GETDATE()`-based computed columns cannot be generated columns; use a view or trigger.

Create table from existing table/query:
```sql
-- Copy structure (the LIKE clause goes inside parentheses)
CREATE TABLE <New Table> (LIKE <Source Table> INCLUDING ALL);
-- Create + populate (like SELECT INTO)
CREATE TABLE NewTable AS SELECT Col1 AS Col2 FROM SourceTable;
```

ROWVERSION replacement via a `BEFORE UPDATE` trigger. (The playbook's original example used an `AFTER UPDATE` trigger that re-updated the same row, which recurses, and had no `RETURN`; this corrected form avoids both):
```sql
CREATE OR REPLACE FUNCTION inc_row_version() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.version_number := OLD.version_number + 1;
  RETURN NEW;
END $$;

CREATE TRIGGER maintain_workitem_version
  BEFORE UPDATE ON workitems
  FOR EACH ROW EXECUTE FUNCTION inc_row_version();
```
For optimistic concurrency, PostgreSQL's system column `xmin` (the transaction id of the last update) works as a free row version that many ORMs support (`xmin` concurrency token in EF Core / Npgsql). It is not stable across dump/restore and not unique across rows.

Syntax (abbreviated):
```sql
CREATE [ [ GLOBAL | LOCAL ] { TEMPORARY | TEMP } | UNLOGGED ] TABLE [ IF NOT EXISTS ]
table_name ( [
{ column_name data_type [ COLLATE collation ] [ column_constraint [ ... ] ]
| table_constraint
| LIKE source_table [ like_option ... ] }
[, ... ]
] )
[ INHERITS ( parent_table [, ... ] ) ]
[ PARTITION BY { RANGE | LIST } ( ... ) ]
[ WITH ( storage_parameter [= value] [, ... ] ) | WITHOUT OIDS ]   -- WITH OIDS removed in PG 12
[ ON COMMIT { PRESERVE ROWS | DELETE ROWS | DROP } ]
[ TABLESPACE tablespace_name ]
```

`column_constraint` supports `GENERATED { ALWAYS | BY DEFAULT } AS IDENTITY`, `UNIQUE`, `PRIMARY KEY`, `REFERENCES ... [ON DELETE action] [ON UPDATE action]`, `DEFERRABLE` options. `table_constraint` adds `EXCLUDE [USING index_method] (...)`.

Examples:
```sql
-- Basic table
CREATE TABLE MyTable
(
Col1 INT PRIMARY KEY,
Col2 VARCHAR(20) NOT NULL
);

-- Column constraints
CREATE TABLE MyTable
(
Col1 INT PRIMARY KEY,
Col2 VARCHAR(20) NOT NULL
  CHECK (Col2 <> ''),
Col3 VARCHAR(100) NULL
  REFERENCES MyOtherTable (Col3)
);
```

## Conversion notes

| Feature | SQL Server | Aurora PostgreSQL |
|---|---|---|
| ANSI compliance | Entry level | Entry level |
| Auto generated enumerator | `IDENTITY` | `GENERATED { BY DEFAULT \| ALWAYS } AS IDENTITY` (preferred over `SERIAL`) |
| Reseed auto generated value | `DBCC CHECKIDENT ('t', RESEED, n)` | `ALTER TABLE t ALTER COLUMN id RESTART WITH n;` or `SELECT setval(pg_get_serial_sequence('t','id'), n);` |
| Computed column | `AS (expr)` / `PERSISTED` | `GENERATED ALWAYS AS (expr)` `VIRTUAL` / `STORED` (PG 18) |
| Index types | `CLUSTERED` / `NONCLUSTERED` | See Indexes |
| Physical storage location | `ON <File Group>` | Not supported |
| Temporary tables | `#TempTable` | `CREATE TEMPORARY TABLE` |
| Global temporary tables | `##GlobalTempTable` | No equivalent: `GLOBAL` is ignored and the table is session-private. Use an unlogged permanent table, or redesign |
| Table variables | `DECLARE @Table` | Not supported — temp table (`CREATE TEMP TABLE … ON COMMIT DROP`), array of a composite type, or a CTE |
| Create table as query | `SELECT… INTO` | `CREATE TABLE… AS` |
| Copy table structure | Not supported | `CREATE TABLE… LIKE` |
| Memory-optimized tables | Supported | N/A |

- Convert `IDENTITY` to `GENERATED BY DEFAULT AS IDENTITY` (closest to SQL Server, which allows `SET IDENTITY_INSERT ON`) or `GENERATED ALWAYS` (with `OVERRIDING SYSTEM VALUE` for loads). `DBCC CHECKIDENT … RESEED` → `ALTER TABLE … ALTER COLUMN … RESTART WITH n` (verified). After loads, `./dbmig reset-identity` syncs all identities.
- `SET IDENTITY_INSERT t ON` → no session switch; insert with `OVERRIDING SYSTEM VALUE` (for `ALWAYS`) or plainly (for `BY DEFAULT`), then reset the identity.
- Drop `ON <File Group>` physical storage clauses; not supported.
- Table variables and memory-optimized tables have no equivalent — redesign required.
- `ROWVERSION`/`TIMESTAMP` not supported — implement with a trigger.
- `SELECT INTO` → `CREATE TABLE … AS`; PostgreSQL also offers `CREATE TABLE … LIKE` to copy structure.
