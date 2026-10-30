# MERGE for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.merge.html

**Conversion category:** Manual (Three star feature compatibility — no automation; rewrite required)
**SCT automation:** No automation

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Row-alias ODKU syntax (verified), NULL-safe multi-table rewrite replacing NOT IN, unique-key and row-count caveats, OUTPUT and concurrency notes; still no MERGE (verified).

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

In-place update on duplicate-key instead of error. MySQL extension (non-ANSI). Reference the proposed row with a **row alias** — `INSERT … VALUES (…) AS new ON DUPLICATE KEY UPDATE col2 = new.col2` (8.0.19+, verified); `VALUES(col)` in this clause is deprecated. In `INSERT … SELECT … ON DUPLICATE KEY UPDATE` you can reference the source table's columns directly (verified).

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
-- preferred on Aurora MySQL 3 / 8.4 (verified): multi-table DML, NULL-safe
START TRANSACTION;
DELETE t FROM TargetTable t
LEFT JOIN SourceTable s ON s.Col1 = t.Col1
WHERE s.Col1 IS NULL;                                   -- WHEN NOT MATCHED BY SOURCE THEN DELETE
INSERT INTO TargetTable (Col1, Col2)
SELECT s.Col1, s.Col2 FROM SourceTable s
ON DUPLICATE KEY UPDATE Col2 = COALESCE(s.Col2, TargetTable.Col2);   -- MATCHED UPDATE + NOT MATCHED INSERT
COMMIT;
-- (the original used NOT IN subqueries, which match nothing if the subquery returns a NULL)
```

## Conversion notes

- Key match condition is mandated by PK/UNIQUE constraints — cannot use an arbitrary `ON` predicate.
- No equivalent for `WHEN NOT MATCHED BY SOURCE` or the `OUTPUT` clause.
- `REPLACE` deletes the violating row (may fail on FK constraints → can fail the whole transaction); `INSERT … ON DUPLICATE KEY UPDATE` updates in place without deleting (safer with FKs).
- For complex MERGE logic, break into constituent `INSERT`/`UPDATE`/`DELETE` statements in one transaction; when the `ON` predicate is not a unique key, use `UPDATE t JOIN s ON … SET …` followed by `INSERT … SELECT … WHERE NOT EXISTS (…)`.
- Still no `MERGE` on Aurora MySQL 3 / 8.4 (verified).
- `ON DUPLICATE KEY UPDATE` fires on **any** unique key of the target, not only the `ON` columns; tables with several unique keys can update the wrong row.
- Affected-row counts: 1 per insert, 2 per update, 0 if unchanged — code that reads `@@ROWCOUNT` after `MERGE` needs adjusting.
- `OUTPUT $action, inserted.*, deleted.*` → no equivalent; capture changes with triggers or by querying before/after inside the transaction.
- Concurrent upserts take gap/next-key locks under `REPEATABLE READ`; retry on deadlock error 1213.

| SQL Server MERGE feature | Aurora MySQL | Comments |
|---|---|---|
| Source in `USING` | `SELECT` query or a table | |
| `ON` predicate | PK/UNIQUE constraints | No custom predicate |
| `WHEN MATCHED THEN UPDATE` | `REPLACE` or `INSERT…ON DUPLICATE KEY UPDATE` | REPLACE deletes (FK risk); ODKU updates in place |
| `WHEN MATCHED THEN DELETE` | `DELETE FROM Target WHERE Key IN (SELECT Key FROM Source)` | |
| `WHEN NOT MATCHED THEN INSERT` | `REPLACE` or `INSERT…ON DUPLICATE KEY UPDATE` | |
| `WHEN NOT MATCHED BY SOURCE UPDATE` | `UPDATE Target t LEFT JOIN Source s ON … SET … WHERE s.Key IS NULL` | NULL-safe |
| `WHEN NOT MATCHED BY SOURCE DELETE` | `DELETE t FROM Target t LEFT JOIN Source s ON … WHERE s.Key IS NULL` | verified |
| `OUTPUT` clause | N/A | |
