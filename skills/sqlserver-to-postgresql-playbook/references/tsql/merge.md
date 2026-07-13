# MERGE

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.merge.html

**Conversion category:** Assisted (three-star feature compatibility, no automation — rewrite to `INSERT … ON CONFLICT`)
**SCT automation:** No automation; SCT action code index: MERGE

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

PostgreSQL 10 does **not** support `MERGE`. Use `INSERT … ON CONFLICT`, which redirects conflicting inserts to an update.

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

Running the same operation repeatedly with `ON CONFLICT` doesn't error — existing rows are redirected to the update clause.

## Conversion notes
- Rewrite `MERGE` as `INSERT … ON CONFLICT (key) DO UPDATE SET ...` (upsert) or `DO NOTHING`.
- `ON CONFLICT` requires a unique/primary-key constraint on the conflict target columns.
- `WHEN NOT MATCHED BY SOURCE THEN DELETE` (deleting target rows absent from source) has no `ON CONFLICT` equivalent — implement with a separate `DELETE ... WHERE NOT EXISTS/NOT IN`.
- `OUTPUT` clause → use `RETURNING`.
- For complex multi-branch MERGE logic, split into discrete `INSERT`/`UPDATE`/`DELETE` statements.
- Note: native `MERGE` is available in later PostgreSQL versions (15+); this playbook targets PostgreSQL 10/13.
