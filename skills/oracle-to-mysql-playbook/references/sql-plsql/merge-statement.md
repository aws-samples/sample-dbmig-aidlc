# MERGE Statement

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.merge.html

**Conversion category:** Manual (★★★ feature compatibility, no automation) — workaround available
**SCT automation:** Action code "Merge" — Aurora MySQL doesn't support `MERGE`.

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
* **`INSERT … ON DUPLICATE KEY UPDATE`** — performs an in-place UPDATE instead of raising a duplicate-key error. MySQL extension, not ANSI.

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

- For complex MERGE logic, break into discrete `INSERT`/`UPDATE`/`DELETE` statements.
