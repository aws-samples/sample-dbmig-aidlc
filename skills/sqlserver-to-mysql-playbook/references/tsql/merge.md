# MERGE for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.merge.html

**Conversion category:** Manual (Three star feature compatibility — no automation; rewrite required)
**SCT automation:** No automation

## SQL Server

`MERGE` is a hybrid DML statement performing `INSERT`/`UPDATE`/`DELETE` on a target table based on a join with a source set. Can return rows via `OUTPUT`. ANSI SQL:2008 compatible with SQL Server extensions.

### Syntax

```sql
MERGE [INTO] <Target Table> [AS] <Table Alias>]
USING <Source Table>
ON <Merge Predicate>
[WHEN MATCHED [AND <Predicate>]
THEN UPDATE SET <Column Assignments...> | DELETE]
[WHEN NOT MATCHED [BY TARGET] [AND <Predicate>]
THEN INSERT [(<Column List>)]
VALUES (<Values List>) | DEFAULT VALUES]
[WHEN NOT MATCHED BY SOURCE [AND <Predicate>]
THEN UPDATE SET <Column Assignments...> | DELETE]
OUTPUT [<Output Clause>]
```

### Examples

```sql
-- One-way sync
MERGE INTO TargetTable AS TGT
USING SourceTable AS SRC ON TGT.Col1 = SRC.Col1
WHEN MATCHED
    THEN UPDATE SET TGT.Col2 = SRC.Col2
WHEN NOT MATCHED
    THEN INSERT (Col1, Col2)
    VALUES (SRC.Col1, SRC.Col2);

-- Conditional two-way sync (NULL = no change, delete missing)
MERGE INTO TargetTable AS TGT
USING SourceTable AS SRC ON TGT.Col1 = SRC.Col1
WHEN MATCHED AND SRC.Col2 IS NOT NULL
    THEN UPDATE SET TGT.Col2 = SRC.Col2
WHEN NOT MATCHED
    THEN INSERT (Col1, Col2)
    VALUES (SRC.Col1, SRC.Col2)
WHEN NOT MATCHED BY SOURCE
    THEN DELETE;
```

## MySQL

Aurora MySQL does **not** support `MERGE`. Alternatives: `REPLACE` and `INSERT… ON DUPLICATE KEY UPDATE`. Both rely on existing PRIMARY KEY / UNIQUE constraints — you cannot define custom `MATCH` predicates.

### REPLACE

Like `INSERT`, but on a PK/UNIQUE violation it first DELETEs the existing row then INSERTs. MySQL extension (non-ANSI).

```sql
REPLACE [INTO] <Table Name> (<Column List>) VALUES (<Values List>)
REPLACE [INTO] <Table Name> SET <ColumnName = VALUE...>
REPLACE [INTO] <Table Name> (<Column List>) SELECT ...
```

### INSERT … ON DUPLICATE KEY UPDATE

In-place update on duplicate-key instead of error. MySQL extension (non-ANSI).

```sql
INSERT [INTO] <Table Name> [<Column List>]
VALUES (<Value List>)
ON DUPLICATE KEY UPDATE <ColumnName = Value...>

INSERT [INTO] <Table Name> [<Column List>]
SELECT ...
ON DUPLICATE KEY UPDATE <ColumnName = Value...>
```

### Examples

```sql
-- One-way sync via REPLACE
REPLACE INTO TargetTable(Col1, Col2)
SELECT Col1, Col2 FROM SourceTable;

-- Conditional two-way sync via constituent statements
DELETE FROM TargetTable
WHERE Col1 NOT IN (SELECT Col1 FROM SourceTable);

INSERT INTO TargetTable (Col1, Col2)
SELECT Col1, Col2 FROM SourceTable AS SRC
WHERE SRC.Col1 NOT IN (SELECT Col1 FROM TargetTable);

UPDATE TargetTable AS TGT
SET Col2 = (
    SELECT COALESCE(SRC.Col2, TGT.Col2)
    FROM SourceTable AS SRC
    WHERE SRC.Col1 = TGT.Col1
)
WHERE TGT.Col1 IN (SELECT Col1 FROM SourceTable);
```

## Conversion notes

- Key match condition is mandated by PK/UNIQUE constraints — cannot use an arbitrary `ON` predicate.
- No equivalent for `WHEN NOT MATCHED BY SOURCE` or the `OUTPUT` clause.
- `REPLACE` deletes the violating row (may fail on FK constraints → can fail the whole transaction); `INSERT … ON DUPLICATE KEY UPDATE` updates in place without deleting (safer with FKs).
- For complex MERGE logic, break into constituent `INSERT`/`UPDATE`/`DELETE` statements.

| SQL Server MERGE feature | Aurora MySQL | Comments |
|---|---|---|
| Source in `USING` | `SELECT` query or a table | |
| `ON` predicate | PK/UNIQUE constraints | No custom predicate |
| `WHEN MATCHED THEN UPDATE` | `REPLACE` or `INSERT…ON DUPLICATE KEY UPDATE` | REPLACE deletes (FK risk); ODKU updates in place |
| `WHEN MATCHED THEN DELETE` | `DELETE FROM Target WHERE Key IN (SELECT Key FROM Source)` | |
| `WHEN NOT MATCHED THEN INSERT` | `REPLACE` or `INSERT…ON DUPLICATE KEY UPDATE` | |
| `WHEN NOT MATCHED BY SOURCE UPDATE` | `UPDATE Target SET … WHERE Key NOT IN (SELECT Key FROM Source)` | |
| `WHEN NOT MATCHED BY SOURCE DELETE` | `DELETE FROM Target WHERE Key NOT IN (SELECT Key FROM Source)` | |
| `OUTPUT` clause | N/A | |
