# MERGE

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.merge.html

**Conversion category:** Assisted (three-star feature compatibility, no automation — rewrite to `INSERT … ON CONFLICT`)
**SCT automation:** No automation; SCT action code index: MERGE

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Native MERGE is now the default (PG 15), with WHEN NOT MATCHED BY SOURCE, RETURNING merge_action() (PG 17) and old/new in RETURNING (PG 18), all verified; ON CONFLICT kept for concurrent upserts; SET-alias and concurrency differences added.

## SQL Server

`MERGE` is a hybrid DML statement performing `INSERT`/`UPDATE`/`DELETE` on a target table based on a join with a source set. It can return rows via `OUTPUT`. Most efficient for non-trivial conditional DML (insert if key absent, update if present; optionally delete target rows not in source). ANSI SQL:2008 compatible, with SQL Server extensions.

Syntax:

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

One-way synchronization example:

```sql
MERGE INTO TargetTable AS TGT
USING SourceTable AS SRC ON TGT.Col1 = SRC.Col1
WHEN MATCHED
  THEN UPDATE SET TGT.Col2 = SRC.Col2
WHEN NOT MATCHED
  THEN INSERT (Col1, Col2)
  VALUES (SRC.Col1, SRC.Col2);
```

Conditional two-way sync with delete:

```sql
MERGE INTO TargetTable AS TGT
USING SourceTable AS SRC ON TGT.Col1 = SRC.Col1
WHEN MATCHED AND SRC.Col2 IS NOT NULL
  THEN UPDATE SET TGT.Col2 = SRC.Col2
WHEN NOT MATCHED
  THEN INSERT (Col1, Col2) VALUES (SRC.Col1, SRC.Col2)
WHEN NOT MATCHED BY SOURCE
  THEN DELETE;
```

## PostgreSQL

**Aurora PostgreSQL 18 has native `MERGE`** (PG 15), with `WHEN NOT MATCHED BY SOURCE`, `RETURNING` and `merge_action()` (PG 17), and `old.`/`new.` row references in `RETURNING` (PG 18). The SQL Server two-way sync example converts almost verbatim (verified on 18.6):

```sql
MERGE INTO TargetTable AS TGT
USING SourceTable AS SRC ON TGT.Col1 = SRC.Col1
WHEN MATCHED AND SRC.Col2 IS NOT NULL
  THEN UPDATE SET Col2 = SRC.Col2          -- no target alias on the SET column
WHEN NOT MATCHED
  THEN INSERT (Col1, Col2) VALUES (SRC.Col1, SRC.Col2)
WHEN NOT MATCHED BY SOURCE
  THEN DELETE
RETURNING merge_action() AS action, old.Col1 AS old_col1, new.Col1 AS new_col1;   -- OUTPUT $action, deleted.*, inserted.*
```

Differences to handle:
- `UPDATE SET TGT.Col2 = …` → `UPDATE SET Col2 = …` (PostgreSQL rejects a qualified SET target).
- `OUTPUT $action, inserted.*, deleted.*` → `RETURNING merge_action(), new.*, old.*`. `OUTPUT … INTO @tbl` → wrap the `MERGE` in a CTE (`WITH m AS (MERGE … RETURNING …) INSERT INTO log SELECT * FROM m`).
- Two source rows matching one target row: both engines raise an error (PostgreSQL: "MERGE command cannot affect row a second time", SQLSTATE 21000, verified).
- **Concurrency:** PostgreSQL `MERGE` does not take the key-range lock that `MERGE … WITH (HOLDLOCK)` takes in SQL Server. Two sessions inserting the same new key can both reach `WHEN NOT MATCHED`, and one fails with a unique violation (verified with duplicate source keys: 23505). For a concurrent single-table upsert keyed on a unique constraint, prefer `INSERT … ON CONFLICT … DO UPDATE`, which is race-free.
- `MERGE` into a simple updatable view works (PG 17, verified). `MERGE` cannot target a foreign table.
- `TOP (n)` in `MERGE` has no equivalent; limit the `USING` subquery instead.

### `INSERT … ON CONFLICT` (concurrent upsert)

```sql
CREATE TABLE EMP_BONUS (
EMPLOYEE_ID NUMERIC,
BONUS_YEAR VARCHAR(4),
SALARY NUMERIC,
BONUS NUMERIC,
PRIMARY KEY (EMPLOYEE_ID, BONUS_YEAR));

INSERT INTO EMP_BONUS (EMPLOYEE_ID, BONUS_YEAR, SALARY)
  SELECT EMPLOYEE_ID, EXTRACT(YEAR FROM NOW()), SALARY
  FROM EMPLOYEES
  WHERE SALARY < 10000
  ON CONFLICT (EMPLOYEE_ID, BONUS_YEAR)
  DO UPDATE SET BONUS = EMP_BONUS.SALARY * 0.5;
```

Running the same operation repeatedly with `ON CONFLICT` doesn't error — existing rows are redirected to the update clause. Use `EXCLUDED.col` for the proposed row's values.

## Conversion notes
- **Default: convert T-SQL `MERGE` to native PostgreSQL `MERGE`**, keeping every `WHEN` branch, including `WHEN NOT MATCHED BY SOURCE`. Remove target-alias qualifiers from `SET` columns.
- Use `INSERT … ON CONFLICT (key) DO UPDATE/DO NOTHING` instead when the statement is a plain single-row or batch upsert that runs concurrently, or the source had `WITH (HOLDLOCK)`/`SERIALIZABLE` to prevent the insert race. `ON CONFLICT` requires a unique/primary-key constraint (or index) on the conflict columns.
- `OUTPUT` → `RETURNING` (`merge_action()`, `old.*`, `new.*`).
- This playbook previously said PostgreSQL has no `MERGE` (written for PostgreSQL 10/13); that no longer applies to Aurora PostgreSQL 15+.
