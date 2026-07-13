# MERGE Statement

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.merge.html

**Conversion category:** Manual (Three-star feature compatibility, no automation; `MERGE` isn't supported by PostgreSQL 13, workaround available via `INSERT … ON CONFLICT`)
**SCT automation:** No automation; SCT action code index → Merge

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

PostgreSQL 13 does NOT support `MERGE`. Use `INSERT … ON CONFLICT` to handle the upsert case: an insert that would cause a conflict is redirected to an update.

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

Running the same operation multiple times does not error, because existing records are redirected to the `DO UPDATE` clause.

## Conversion notes

- No native `MERGE` in PostgreSQL 13 (the Aurora PostgreSQL version targeted by this playbook). Note: PostgreSQL 15+ does add native `MERGE`; check your Aurora PostgreSQL engine version.
- Map `WHEN NOT MATCHED THEN INSERT` + `WHEN MATCHED THEN UPDATE` to `INSERT … ON CONFLICT (key) DO UPDATE`.
- The conflict target must be a unique/PK constraint or index.
- Oracle's `WHEN MATCHED … DELETE WHERE` has no direct `ON CONFLICT` equivalent; handle deletes with a separate `DELETE` statement or a CTE-based approach.
- In `DO UPDATE`, reference the proposed row with `EXCLUDED.<col>` and the existing row with the table name.
