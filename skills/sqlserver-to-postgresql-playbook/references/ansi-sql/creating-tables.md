# Creating Tables (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.tables.html

**Conversion category:** Assisted (Three-star compatibility, four-star automation)
**SCT automation:** SCT action code index: Creating Tables. Key differences: auto-generated value column differs; can't use physical attribute `ON <File Group>`; no table variables or memory-optimized tables.

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

ANSI/ISO entry-level conformant `CREATE TABLE` plus Aurora extensions (most common: in-line index definition). Two table scopes: standard and temporary (`CREATE GLOBAL TEMPORARY TABLE`).

Generated columns (PostgreSQL 12+):
```sql
CREATE TABLE tst_gen(
n NUMERIC,
n_gen GENERATED ALWAYS AS (n*0.01)
);
```

Create table from existing table/query:
```sql
-- Copy structure
CREATE TABLE <New Table> LIKE <Source Table>;
-- Create + populate (like SELECT INTO)
CREATE TABLE NewTable AS SELECT Col1 AS Col2 FROM SourceTable;
```

ROWVERSION replacement via trigger:
```sql
CREATE OR REPLACE FUNCTION IncByOne()
  RETURNS TRIGGER
  AS $$
  BEGIN
    UPDATE WorkItems SET VersionNumber = VersionNumber+1
    WHERE WorkItemID = OLD.WorkItemID;
  END; $$
  LANGUAGE PLPGSQL;

CREATE TRIGGER MaintainWorkItemVersionNumber
  AFTER UPDATE OF WorkItems
  FOR EACH ROW
  EXECUTE PROCEDURE IncByOne();
```

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
[ WITH ( storage_parameter [= value] [, ... ] ) | WITH OIDS | WITHOUT OIDS ]
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
| Auto generated enumerator | `IDENTITY` | `SERIAL` |
| Reseed auto generated value | `DBCC CHECKIDENT` | N/A |
| Index types | `CLUSTERED` / `NONCLUSTERED` | See Indexes |
| Physical storage location | `ON <File Group>` | Not supported |
| Temporary tables | `#TempTable` | `CREATE TEMPORARY TABLE` |
| Global temporary tables | `##GlobalTempTable` | `CREATE GLOBAL TEMPORARY TABLE` |
| Table variables | `DECLARE @Table` | Not supported |
| Create table as query | `SELECT… INTO` | `CREATE TABLE… AS` |
| Copy table structure | Not supported | `CREATE TABLE… LIKE` |
| Memory-optimized tables | Supported | N/A |

- Convert `IDENTITY` to `SERIAL` (or `GENERATED ... AS IDENTITY`). No reseed equivalent for `DBCC CHECKIDENT`.
- Drop `ON <File Group>` physical storage clauses; not supported.
- Table variables and memory-optimized tables have no equivalent — redesign required.
- `ROWVERSION`/`TIMESTAMP` not supported — implement with a trigger.
- `SELECT INTO` → `CREATE TABLE … AS`; PostgreSQL also offers `CREATE TABLE … LIKE` to copy structure.
