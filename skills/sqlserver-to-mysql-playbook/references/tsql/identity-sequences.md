# Identity and sequences for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.identitysequences.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** Three star automation level

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

SQL Server persists `IDENTITY` metadata to disk — sequence continues after restart. Aurora MySQL keeps the auto-increment counter **in memory only**; on restart, the first INSERT computes the counter as `SELECT MAX(<col>) FROM <table> FOR UPDATE` + increment (or 1 if empty). Every restart cancels any `AUTO_INCREMENT = <Value>` table option. Explicit values are allowed; an explicit value greater than the counter resets the counter to it.

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
SET @@auto_increment_increment=10;
SHOW VARIABLES LIKE 'auto_inc%';
```

## Conversion notes

- `IDENTITY` → `AUTO_INCREMENT`; application must insert NULL/0 (or omit the column) to trigger generation.
- `SEQUENCE` objects → not supported; build a custom solution if table-independent sequences are needed.
- Ensure `AUTO_INCREMENT` columns are indexed and have no `DEFAULT`.
- Last value behavior differs: re-evaluated as `MAX(value)+1` on each restart (vs SQL Server's persisted value).
- Seed/interval params are global, not per-column.
- Non-PK auto-enumerator columns and compound PKs with auto-enumerator are **not supported** — implement an application enumerator.

| Feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Independent `SEQUENCE` | `CREATE SEQUENCE` | Not supported | |
| Auto enumerator column | `IDENTITY` | `AUTO_INCREMENT` | |
| Reseed | `DBCC CHECKIDENT` | `ALTER TABLE … AUTO_INCREMENT = <v>` | |
| Column restrictions | Numeric | Numeric, indexed, no `DEFAULT` | |
| Seed/interval control | `CREATE/ALTER TABLE` | `auto_increment_increment`/`_offset` | Global, not per-column |
| Sequence init | Maintained across restarts | Re-initialized each restart | `MAX+1` |
| Explicit values | Not allowed (needs `SET IDENTITY_INSERT ON`) | Supported | NULL/0 triggers; larger value reseeds |
| Non-PK auto enumerator | Supported | Not supported | App enumerator |
| Compound PK with auto enumerator | Supported | Not supported | App enumerator |
