# Anonymous Block and PostgreSQL DO

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.block.html

**Conversion category:** Assisted (Four-star feature compatibility, three-star automation; different syntax may require code rewrite)
**SCT automation:** Three-star automation level; SCT action code index → Stored Procedures

## Oracle

Oracle PL/SQL is a procedural extension of SQL, organized into blocks via `DECLARE`, `BEGIN`, `EXCEPTION`, `END`. An **anonymous block** is unnamed/unstored PL/SQL code with:
- Declarative section (optional)
- Executable section (mandatory — at least one statement)
- Exception-handling section (optional)

```sql
SET SERVEROUTPUT ON;
BEGIN
  DBMS_OUTPUT.PUT_LINE('hello world');
END;
/
-- hello world
-- PL/SQL procedure successfully completed.
```

More complex example (cursor FOR-loop + conditional + exception handling):

```sql
SET SERVEROUTPUT ON;
DECLARE
  v_sal_chk        NUMBER;
  v_emp_work_years NUMBER;
  v_sql_cmd        VARCHAR2(2000);
BEGIN
  FOR v IN (SELECT EMPLOYEE_ID, FIRST_NAME||' '||LAST_NAME AS EMP_NAME, HIRE_DATE, SALARY FROM EMPLOYEES)
  LOOP
    v_emp_work_years := EXTRACT(YEAR FROM SYSDATE) - EXTRACT(YEAR FROM v.hire_date);
    IF v_emp_work_years >= 10 AND v.salary <= 6000 THEN
      DBMS_OUTPUT.PUT_LINE('Consider a Bonus for: '||v.emp_name);
    END IF;
  END LOOP;
EXCEPTION WHEN OTHERS THEN
  DBMS_OUTPUT.PUT_LINE('CODE ERR: '||sqlerrm);
END;
/
```

## PostgreSQL

PostgreSQL runs unstored PL/pgSQL via the `DO` statement. PL/pgSQL has the same block structure (declarative optional, executable mandatory, exception optional). Code is wrapped in dollar-quoting (`$$ … $$`).

```sql
SET CLIENT_MIN_MESSAGES = 'debug';
-- Equivalent to Oracle SET SERVEROUTPUT ON

DO $$
  BEGIN
    RAISE DEBUG USING MESSAGE := 'hello world';
  END $$;
-- DEBUG: hello world
-- DO
```

Converted "employee bonus" example:

```sql
DO $$
  DECLARE
    v_sal_chk DOUBLE PRECISION;
    v_emp_work_years DOUBLE PRECISION;
    v_sql_cmd CHARACTER VARYING(2000);
    v RECORD;
  BEGIN
  FOR v IN
    SELECT employee_id, CONCAT_WS('', first_name, ' ', last_name) AS emp_name, hire_date, salary FROM employees
  LOOP
    v_emp_work_years := EXTRACT (YEAR FROM now()) - EXTRACT (YEAR FROM v.hire_date);
    IF v_emp_work_years >= 10 AND v.salary <= 6000 THEN
      RAISE DEBUG USING MESSAGE := CONCAT_WS('', 'Consider a Salary Raise for: ', v.emp_name);
    END IF;
  END LOOP;
  EXCEPTION
    WHEN others THEN
      RAISE DEBUG USING MESSAGE := CONCAT_WS('', 'CODE ERR: ', SQLERRM);
  END $$;
```

## Conversion notes

- Wrap the block in `DO $$ … $$;` — there is no bare `BEGIN … END; /` anonymous block in PG.
- Loop variables must be explicitly declared (e.g., `v RECORD;`) in PL/pgSQL; Oracle implicitly declares the FOR-loop variable.
- `DBMS_OUTPUT.PUT_LINE` → `RAISE NOTICE`/`RAISE DEBUG`; enable output with `SET CLIENT_MIN_MESSAGES` instead of `SET SERVEROUTPUT ON`.
- `SYSDATE` → `now()`; string concat `||` works, but the playbook uses `CONCAT_WS` to handle NULLs.
- `SQLERRM` is available in both for exception messages.
- Type names differ (`NUMBER`→`DOUBLE PRECISION`/`NUMERIC`, `VARCHAR2`→`CHARACTER VARYING`).
