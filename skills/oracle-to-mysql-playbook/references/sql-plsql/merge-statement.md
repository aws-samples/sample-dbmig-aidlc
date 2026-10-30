# MERGE Statement

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.merge.html

**Conversion category:** Manual (★★★ feature compatibility, no automation) — workaround available
**SCT automation:** Action code "Merge" — Aurora MySQL doesn't support `MERGE`.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Still no MERGE on 3 / 8.4 (verified); added row-alias syntax (VALUES() deprecated), a verified conversion of the Oracle example, unique-key and NOT IN pitfalls, LEFT JOIN delete, affected-row counts, gap-lock deadlocks.

## Oracle

`MERGE` (a.k.a. UPSERT) conditionally performs `INSERT`/`UPDATE`/`DELETE` on a target based on a join with a source. It is deterministic: a row processed once cannot be processed again by the same statement.

```sql
CREATE TABLE EMP_BONUS(EMPLOYEE_ID NUMERIC, BONUS_YEAR VARCHAR2(4),
  SALARY NUMERIC, BONUS NUMERIC, PRIMARY KEY (EMPLOYEE_ID, BONUS_YEAR));

MERGE INTO EMP_BONUS E1
USING (SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID FROM EMPLOYEES) E2
  ON (E1.EMPLOYEE_ID = E2.EMPLOYEE_ID)
WHEN MATCHED THEN
  UPDATE SET E1.BONUS = E2.SALARY * 0.5
  DELETE WHERE (E1.SALARY >= 10000)
WHEN NOT MATCHED THEN
  INSERT (E1.EMPLOYEE_ID, E1.BONUS_YEAR, E1.SALARY, E1.BONUS)
  VALUES (E2.EMPLOYEE_ID, EXTRACT(YEAR FROM SYSDATE), E2.SALARY, E2.SALARY * 0.5)
  WHERE (E2.SALARY < 10000);
```

## MySQL

Aurora MySQL has no `MERGE`. Use `REPLACE` or `INSERT … ON DUPLICATE KEY UPDATE` — both rely on existing PRIMARY KEY / UNIQUE constraints (no custom MATCH predicate).

* **`REPLACE`** — INSERT, but on a PK/UNIQUE violation it DELETEs the existing row then INSERTs. MySQL extension, not ANSI.
* **`INSERT … ON DUPLICATE KEY UPDATE`** — performs an in-place UPDATE instead of raising a duplicate-key error. MySQL extension, not ANSI. Reference the proposed row with a **row alias** (`VALUES (…) AS new … UPDATE col2 = new.col2`, MySQL 8.0.19+, verified); the `VALUES(col)` function in this clause is deprecated since 8.0.20.
* Aurora MySQL 3 and 8.4 still have **no `MERGE`** (verified).

```sql
-- REPLACE syntax
REPLACE [INTO] <Table> (<Columns>) VALUES (<Values>)
REPLACE [INTO] <Table> SET col = value...
REPLACE [INTO] <Table> (<Columns>) SELECT ...

-- INSERT ... ON DUPLICATE KEY UPDATE syntax
INSERT [INTO] <Table> [<Columns>] VALUES (<Values>)
  ON DUPLICATE KEY UPDATE col = value...
INSERT [INTO] <Table> SET col = value... ON DUPLICATE KEY UPDATE col = value...
INSERT [INTO] <Table> [<Columns>] SELECT ... ON DUPLICATE KEY UPDATE col = value...
```

One-way sync with `REPLACE`:
```sql
CREATE TABLE SourceTable (Col1 INT NOT NULL PRIMARY KEY, Col2 VARCHAR(20) NOT NULL);
CREATE TABLE TargetTable (Col1 INT NOT NULL PRIMARY KEY, Col2 VARCHAR(20) NOT NULL);
INSERT INTO SourceTable VALUES (2,'Source2'),(3,'Source3'),(4,'Source4');
INSERT INTO TargetTable VALUES (1,'Target1'),(2,'Target2'),(3,'Target3');

REPLACE INTO TargetTable(Col1, Col2) SELECT Col1, Col2 FROM SourceTable;
-- Result: 1/Target1, 2/Source2, 3/Source3, 4/Source4
```

Conditional two-way sync (NULL = no change; DELETE rows missing from source):
```sql
TRUNCATE TABLE SourceTable;
INSERT INTO SourceTable(Col1, Col2) VALUES (3, NULL),(4,'NewSource4'),(5,'Source5');

DELETE FROM TargetTable WHERE Col1 NOT IN (SELECT Col1 FROM SourceTable);

INSERT INTO TargetTable (Col1, Col2)
SELECT Col1, Col2 FROM SourceTable AS SRC
WHERE SRC.Col1 NOT IN (SELECT Col1 FROM TargetTable);

UPDATE TargetTable AS TGT
SET Col2 = (SELECT COALESCE(SRC.Col2, TGT.Col2) FROM SourceTable AS SRC WHERE SRC.Col1 = TGT.Col1)
WHERE TGT.Col1 IN (SELECT Col1 FROM SourceTable);
-- Result: 3/Source3, 4/NewSource4, 5/Source5
```

## Conversion notes

Neither workaround is a full `MERGE` replacement:
- Match conditions are dictated by PK/UNIQUE constraints — cannot use an explicit predicate.
- No equivalent for `WHEN NOT MATCHED BY SOURCE` or the `OUTPUT` clause.
- `REPLACE` DELETEs the violating row — may fail on foreign keys and abort the transaction. `INSERT … ON DUPLICATE KEY UPDATE` updates in place (safer with FKs).

| Oracle MERGE feature | Aurora MySQL |
|---|---|
| Source set in `USING` | `SELECT` query or table |
| `ON` predicate | PK/UNIQUE constraint on target |
| `WHEN MATCHED THEN UPDATE` | `REPLACE` or `INSERT … ON DUPLICATE KEY UPDATE` |
| `WHEN MATCHED THEN DELETE` | `DELETE FROM Target WHERE Key IN (SELECT Key FROM Source)` |
| `WHEN NOT MATCHED THEN INSERT` | `REPLACE` or `INSERT … ON DUPLICATE KEY UPDATE` |

- For complex MERGE logic, break into discrete `INSERT`/`UPDATE`/`DELETE` statements, in one transaction.

### Converting the Oracle example (verified on Aurora MySQL 3.13 and 8.4.8)

```sql
START TRANSACTION;
-- WHEN MATCHED THEN UPDATE … / WHEN NOT MATCHED THEN INSERT … WHERE salary < 10000
INSERT INTO emp_bonus (employee_id, bonus_year, salary, bonus)
SELECT e.employee_id, YEAR(NOW()), e.salary, e.salary * 0.5
FROM employees e
WHERE e.salary < 10000
   OR EXISTS (SELECT 1 FROM emp_bonus b WHERE b.employee_id = e.employee_id)
ON DUPLICATE KEY UPDATE bonus = VALUES(salary) * 0.5;      -- or a row alias with INSERT … VALUES
-- … DELETE WHERE (salary >= 10000)  (only rows that were matched/updated)
DELETE b FROM emp_bonus b JOIN employees e ON e.employee_id = b.employee_id
WHERE b.salary >= 10000;
COMMIT;
```

- The `ON` predicate of Oracle `MERGE` must match a **PRIMARY KEY or UNIQUE** key on the target for `ON DUPLICATE KEY UPDATE`. If it doesn't (Oracle allows any join predicate), use a multi-table `UPDATE t JOIN s ON …` followed by `INSERT … SELECT … WHERE NOT EXISTS`.
- `ON DUPLICATE KEY UPDATE` reacts to **any** unique key on the target, not only the one you meant; a table with several unique keys can update the wrong row.
- "Delete target rows not in source" → `DELETE t FROM target t LEFT JOIN source s ON s.key = t.key WHERE s.key IS NULL` (verified); prefer it to `NOT IN (subquery)`, which returns nothing if the subquery has a NULL.
- Affected-row counts differ: `ON DUPLICATE KEY UPDATE` reports 1 per insert and 2 per update (0 if unchanged), so code that checks `SQL%ROWCOUNT` must be adjusted.
- `INSERT … ON DUPLICATE KEY UPDATE` takes next-key/gap locks under `REPEATABLE READ`; concurrent upserts into the same key range can deadlock. Retry on error 1213.
