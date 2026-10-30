# MERGE Statement

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.merge.html

**Conversion category:** Automatic/Assisted on Aurora PostgreSQL 15+ (native `MERGE`). The original playbook rated it Manual because it targeted PostgreSQL 13, which had no `MERGE`. Oracle-only clauses need a mechanical rewrite (below).
**SCT automation:** No automation; SCT action code index → Merge

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): native `MERGE` (PG 15) plus PG 17 `RETURNING`/`merge_action()`/`NOT MATCHED BY SOURCE`; the playbook example converted and verified; Oracle→PG rewrite rules; MERGE vs ON CONFLICT concurrency.

## Oracle

`MERGE` performs conditional `INSERT`, `UPDATE`, or `DELETE` on a target table in a single statement based on a join with a source — avoiding multiple separate DML statements. `MERGE` is deterministic: a row processed once cannot be processed again by the same statement. Also known as `UPSERT`.

```sql
CREATE TABLE EMP_BONUS(EMPLOYEE_ID NUMERIC, BONUS_YEAR VARCHAR2(4),
SALARY NUMERIC, BONUS NUMERIC, PRIMARY KEY (EMPLOYEE_ID, BONUS_YEAR));

MERGE INTO EMP_BONUS E1
USING (SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID
       FROM EMPLOYEES) E2
ON (E1.EMPLOYEE_ID = E2.EMPLOYEE_ID)
WHEN MATCHED THEN
  UPDATE SET E1.BONUS = E2.SALARY * 0.5
  DELETE WHERE (E1.SALARY >= 10000)
WHEN NOT MATCHED THEN
  INSERT (E1.EMPLOYEE_ID, E1.BONUS_YEAR, E1.SALARY, E1.BONUS)
  VALUES (E2.EMPLOYEE_ID, EXTRACT(YEAR FROM SYSDATE), E2.SALARY, E2.SALARY * 0.5)
  WHERE (E2.SALARY < 10000);
```

## PostgreSQL

PostgreSQL 15+ has native SQL-standard `MERGE`. PostgreSQL 17 adds `RETURNING` (with `merge_action()`), `WHEN NOT MATCHED BY SOURCE`, and `MERGE` into updatable views. The Oracle example converts as follows (verified on Aurora PostgreSQL 18.6, with the expected `UPDATE`/`DELETE`/`INSERT` actions):

```sql
MERGE INTO emp_bonus e1
USING (SELECT employee_id, first_name, salary, department_id FROM employees) e2
ON (e1.employee_id = e2.employee_id)
WHEN MATCHED AND e1.salary >= 10000 THEN          -- Oracle: UPDATE ... DELETE WHERE (E1.SALARY >= 10000)
  DELETE
WHEN MATCHED THEN
  UPDATE SET bonus = e2.salary * 0.5               -- no target alias on the SET column
WHEN NOT MATCHED AND e2.salary < 10000 THEN        -- Oracle: INSERT ... WHERE (E2.SALARY < 10000)
  INSERT (employee_id, bonus_year, salary, bonus)
  VALUES (e2.employee_id, extract(year from now())::text, e2.salary, e2.salary * 0.5)
RETURNING merge_action(), e1.employee_id;         -- PG 17+, optional
```

Rewrite rules for Oracle `MERGE`:

| Oracle | PostgreSQL |
|---|---|
| `WHEN MATCHED THEN UPDATE SET e1.col = …` | `WHEN MATCHED THEN UPDATE SET col = …` (target columns are **not** alias-qualified) |
| `UPDATE … WHERE cond` | `WHEN MATCHED AND cond THEN UPDATE …` |
| `UPDATE … DELETE WHERE cond` | a `WHEN MATCHED AND cond' THEN DELETE` branch **before** the update branch. Oracle evaluates `DELETE WHERE` on the *updated* values; if `SET` changes a column used in `cond`, rewrite `cond'` in terms of the new value (for example `e2.salary * 0.5 >= x`). |
| `WHEN NOT MATCHED THEN INSERT (e1.c1, …) VALUES (…) WHERE cond` | `WHEN NOT MATCHED AND cond THEN INSERT (c1, …) VALUES (…)` |
| — | `WHEN NOT MATCHED BY SOURCE THEN DELETE` (PG 17+): target rows with no source row, which Oracle needs a separate `DELETE` for |
| `ORA-30926: unable to get a stable set of rows` | `ERROR 21000: MERGE command cannot affect row a second time` (verified); de-duplicate the source |
| `LOG ERRORS INTO …` | not supported; see `insert-from-select.md` |

`WHEN` clauses are evaluated **in order** and the first match wins, so put the more specific `AND` conditions first.

**`MERGE` vs `INSERT … ON CONFLICT`.** `MERGE` is not concurrency-safe as an upsert: two sessions inserting the same new key concurrently can both reach `WHEN NOT MATCHED` and one fails with a unique violation. Oracle `MERGE` has the same race. `INSERT … ON CONFLICT` is atomic for a single unique key. Use `MERGE` for faithful conversion of Oracle `MERGE` (multi-branch, delete, conditions). Use `ON CONFLICT` only for simple single-table upserts under heavy concurrent insert of the same keys:

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

Running the same operation multiple times does not error, because existing records are redirected to the `DO UPDATE` clause. (This `ON CONFLICT` form is **not** semantically equivalent to the Oracle `MERGE` above: it matches on the full primary key `(employee_id, bonus_year)` instead of `employee_id`, and it has no delete branch.)

## Conversion notes

- **Default on Aurora PostgreSQL 18: convert Oracle `MERGE` to native `MERGE`** with the rewrite rules above. Do not convert to `ON CONFLICT` unless it is a plain upsert.
- `MERGE … RETURNING` (PG 17+) replaces Oracle code that re-queries the target to find what changed.
- `ON CONFLICT`: the conflict target must be a unique/PK constraint or index. In `DO UPDATE`, reference the proposed row with `EXCLUDED.<col>` and the existing row with the table name.
- On PostgreSQL ≤ 14 (not a recommended target) `MERGE` does not exist; there the old `ON CONFLICT` and separate `DELETE` approach applies.
