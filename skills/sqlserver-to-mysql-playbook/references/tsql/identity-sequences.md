# Identity and sequences for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.identitysequences.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** Three star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected counter persistence (persisted since MySQL 8.0) and the non-PK/compound-PK limits (both work under index rules — verified); SET GLOBAL denied; LAST_INSERT_ID semantics, IDENT_CURRENT caching, sequence-table pattern, 8.4 float restriction, toolkit reseed.

## SQL Server

Three mechanisms for auto-generated values: the `IDENTITY` column property, `SEQUENCE` objects, and the `IDENTITY`/`NEWSEQUENTIALID` functions.

### IDENTITY

A single numeric column per table can be `IDENTITY` (seed, increment). Doesn't enforce uniqueness/indexing by itself. Retrieve values via `@@IDENTITY`, `SCOPE_IDENTITY`, `IDENT_CURRENT`. Manage via `DBCC CHECKIDENT`.

```sql
IDENTITY [(<Seed Value>, <Increment Value>)]

CREATE TABLE MyTABLE
(
    Col1 INT NOT NULL PRIMARY KEY NONCLUSTERED IDENTITY(1,1),
    Col2 VARCHAR(20) NOT NULL
);

DECLARE @LastIdent INT;
INSERT INTO MyTable(Col2) VALUES('SomeString');
SET @LastIdent = SCOPE_IDENTITY();

-- reseed
DBCC CHECKIDENT (<Table>, RESEED, <Seed Value>);
```

### SEQUENCE

Table-independent objects; retrieve with `NEXT VALUE FOR`. Advantages: get value before INSERT, share across tables/columns, easier restart, value ranges via `sp_sequence_get_range`.

```sql
CREATE SEQUENCE <Sequence Name> [AS <Integer Data Type> ]
START WITH <Seed Value>
INCREMENT BY <Increment Value>;

ALTER SEQUENCE <Sequence Name>
RESTART [WITH <Reseed Value>]
INCREMENT BY <New Increment Value>;

CREATE SEQUENCE MySequence AS INT START WITH 1 INCREMENT BY 1;
CREATE TABLE MyTable
(
    Col1 INT NOT NULL PRIMARY KEY NONCLUSTERED DEFAULT (NEXT VALUE FOR MySequence),
    Col2 VARCHAR(20) NULL
);
```

### Sequential functions

`IDENTITY(<Data Type> [, <Seed>, <Increment>])` — only in `SELECT … INTO`. `NEWSEQUENTIALID()` — monotonic GUID, only as a `DEFAULT` on a `UNIQUEIDENTIFIER` column.

## MySQL

Aurora MySQL uses the `AUTO_INCREMENT` column property (similar to `IDENTITY`). No table-independent `SEQUENCE` objects. To generate the next value, omit the column from the INSERT (or insert NULL/0). Retrieve last value with `LAST_INSERT_ID`. Each table can have only **one** `AUTO_INCREMENT` column, which must be indexed or a primary key. Positive numbers only.

Server parameters: `auto_increment_increment` (interval), `auto_increment_offset` (start) — **global**, affect all such columns. Reseed via `ALTER TABLE <Table> AUTO_INCREMENT = <Value>`.

### Syntax

```sql
CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <Table Name>
(<Column Name> <Data Type> [NOT NULL | NULL]
AUTO_INCREMENT [UNIQUE [KEY]] [[PRIMARY] KEY]...
```

### Sequence value initialization (critical difference)

*(corrected)* Since MySQL 8.0 the `AUTO_INCREMENT` counter is **persisted** (redo log + data dictionary), so on Aurora MySQL 3 and 8.4 it survives restarts and failovers like SQL Server `IDENTITY`. The original text described MySQL 5.7 (counter recomputed as `MAX(col)+1` after restart). Explicit values are allowed; an explicit value greater than the counter moves the counter past it (verified: 10 → next 11); `ALTER TABLE … AUTO_INCREMENT = n` below the current maximum is silently raised to `MAX+1` (verified).

### Examples

```sql
CREATE TABLE MyTable
(
    Col1 INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Col2 VARCHAR(20) NOT NULL
);

INSERT INTO MyTable (Col2) VALUES ('AI column omitted');        -- 1
INSERT INTO MyTable (Col1, Col2) VALUES (NULL, 'Explicit NULL'); -- 2
INSERT INTO MyTable (Col1, Col2) VALUES (10, 'Explicit value');  -- 10
INSERT INTO MyTable (Col2) VALUES ('Post explicit value');       -- 11

-- reseed
ALTER TABLE MyTable AUTO_INCREMENT = 30;

-- change increment (affects ALL auto_increment columns)
SET SESSION auto_increment_increment = 10;   -- session scope; SET GLOBAL is denied to the Aurora master user (verified)
SHOW VARIABLES LIKE 'auto_inc%';
```

## Conversion notes

- `IDENTITY` → `AUTO_INCREMENT`; application must insert NULL/0 (or omit the column) to trigger generation.
- `SEQUENCE` objects → not supported; build a custom solution if table-independent sequences are needed.
- Ensure `AUTO_INCREMENT` columns are indexed and have no `DEFAULT`.
- Last value: persisted across restarts on Aurora MySQL 3 / 8.4 (as in SQL Server). Gaps appear after rollbacks and with `innodb_autoinc_lock_mode` = 2 (default, verified), as with `IDENTITY`.
- Seed/interval params are global, not per-column.
- *(corrected)* A non-PK `AUTO_INCREMENT` column works if it is the **first column of some index** (for example `UNIQUE (col)`), and a compound PK works if the `AUTO_INCREMENT` column is the **first** PK column; as a later PK column it fails with error 1075 (all verified).
- `SCOPE_IDENTITY()` / `@@IDENTITY` → `LAST_INSERT_ID()` (per connection; for a multi-row insert it returns the **first** generated value). `IDENT_CURRENT('t')` → `SELECT AUTO_INCREMENT FROM information_schema.tables …` (cached for `information_schema_stats_expiry` = 86400 s, verified — set the session value to 0 for a fresh number).
- `SET IDENTITY_INSERT t ON` → not needed: just insert the explicit value (or 0/NULL to generate).
- `IDENTITY(1,1)` seed → `AUTO_INCREMENT = <seed>` table option; per-column increment other than 1 has no equivalent.
- `CREATE SEQUENCE` / `NEXT VALUE FOR` → a sequence table with `UPDATE seq SET id = LAST_INSERT_ID(id + 1); SELECT LAST_INSERT_ID();` (verified pattern, concurrency-safe per session) wrapped in a function or procedure. `sp_sequence_get_range` → `LAST_INSERT_ID(id + n)`.
- Use integer types: Aurora MySQL 8.4 rejects `AUTO_INCREMENT` on `FLOAT`/`DOUBLE` (error 1063, verified); `DECIMAL(p,0)` identities → `BIGINT`.
- Toolkit: `./dbmig migrate-data` reseeds `AUTO_INCREMENT` to `MAX+1` after the load.

| Feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Independent `SEQUENCE` | `CREATE SEQUENCE` | Not supported | |
| Auto enumerator column | `IDENTITY` | `AUTO_INCREMENT` | |
| Reseed | `DBCC CHECKIDENT` | `ALTER TABLE … AUTO_INCREMENT = <v>` | |
| Column restrictions | Numeric | Numeric, indexed, no `DEFAULT` | |
| Seed/interval control | `CREATE/ALTER TABLE` | `auto_increment_increment`/`_offset` | Global, not per-column |
| Sequence init | Maintained across restarts | Maintained across restarts (MySQL 8.0+) | corrected |
| Explicit values | Not allowed (needs `SET IDENTITY_INSERT ON`) | Supported | NULL/0 triggers; larger value reseeds |
| Non-PK auto enumerator | Supported | Supported if first column of an index | verified |
| Compound PK with auto enumerator | Supported | Supported as the first PK column only | verified (1075 otherwise) |
