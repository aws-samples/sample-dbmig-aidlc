# User-Defined Functions (UDFs)

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.udfs.html

**Conversion category:** Assisted (Three-star feature compatibility, four-star automation; syntax/option differences)
**SCT automation:** Four-star automation level; SCT action code index → Stored Procedures

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): volatility (`IMMUTABLE`/`STABLE`/`PARALLEL SAFE`), SQL-standard bodies, available languages on Aurora 18 (no PL/Python/Java, verified), `aws_lambda` for external logic.

## Oracle

Oracle UDFs can be written in PL/SQL, Java, or C, extending SQL with custom logic. They can appear wherever built-in SQL functions can: in `SELECT` (scalar), DML, and `WHERE`/`GROUP BY`/`ORDER BY`/`HAVING`/`CONNECT BY`/`START WITH` clauses.

```sql
CREATE OR REPLACE FUNCTION TOTAL_EMP_SAL_BY_YEARS
(p_hire_date DATE, p_current_sal NUMBER)
RETURN NUMBER
AS
  v_years_of_service NUMBER;
  v_total_sal_by_years NUMBER;
BEGIN
  SELECT EXTRACT(YEAR FROM SYSDATE) - EXTRACT(YEAR FROM to_date(p_hire_date))
  INTO v_years_of_service FROM dual;
  v_total_sal_by_years := p_current_sal * v_years_of_service;
  RETURN v_total_sal_by_years;
END;
/

SELECT EMPLOYEE_ID, FIRST_NAME, TOTAL_EMP_SAL_BY_YEARS(HIRE_DATE, SALARY) AS TOTAL_SALARY
FROM EMPLOYEES;
```

## PostgreSQL

PostgreSQL creates UDFs with `CREATE FUNCTION`; PL/pgSQL is the primary migration language. Privilege: `USAGE` on the language.

Converted equivalent:

```sql
CREATE OR REPLACE FUNCTION total_emp_sal_by_years
(P_HIRE_DATE DATE, P_CURRENT_SAL NUMERIC)
RETURNS NUMERIC
AS
$BODY$
DECLARE
  V_YEARS_OF_SERVICE NUMERIC;
  V_TOTAL_SAL_BY_YEARS NUMERIC;
BEGIN
  SELECT EXTRACT(YEAR FROM NOW()) - EXTRACT(YEAR FROM (P_HIRE_DATE)) INTO V_YEARS_OF_SERVICE;
  V_TOTAL_SAL_BY_YEARS := P_CURRENT_SAL * V_YEARS_OF_SERVICE;
  RETURN V_TOTAL_SAL_BY_YEARS;
END;
$BODY$
LANGUAGE PLPGSQL;

SELECT EMPLOYEE_ID, FIRST_NAME, TOTAL_EMP_SAL_BY_YEARS(HIRE_DATE, SALARY) AS TOTAL_SALARY
FROM EMPLOYEES;
```

## Conversion notes

- `RETURN <type>` → `RETURNS <type>`; type names map (`NUMBER`→`NUMERIC`, etc.).
- Drop `FROM dual` — PostgreSQL allows bare `SELECT expr INTO var;`.
- `SYSDATE` → `LOCALTIMESTAMP(0)` / `NOW()` (both fixed at transaction start; `clock_timestamp()` advances).
- Oracle `DETERMINISTIC` → `IMMUTABLE` (required for use in expression indexes). Otherwise mark `STABLE` when the function only reads tables, and `PARALLEL SAFE` when it can run in parallel workers. Wrong volatility silently disables index use or caches stale results.
- Simple one-expression functions: use `LANGUAGE sql` with an SQL-standard body (`RETURN expr`, PG 14+). SQL functions can be inlined into the calling query, which avoids per-row PL/pgSQL call overhead.
- Oracle `RESULT_CACHE` has no equivalent; drop it.
- Dollar-quote the body (`$$ … $$` or named `$BODY$ … $BODY$`) and add `LANGUAGE PLPGSQL`.
- UDFs can still be used inline in queries as in Oracle.
- Oracle UDFs in Java/C require full reimplementation. On Aurora PostgreSQL 18 the available procedural languages are PL/pgSQL, PL/Perl, PL/Tcl and **PL/v8 (JavaScript)**, plus **`pg_tle`** for trusted-language extensions. **PL/Python, PL/Java and custom C extensions are not available** (checked against `pg_available_extensions` on 18.6). Logic that needs other runtimes or libraries can move to AWS Lambda and be called with `aws_lambda.invoke(...)` (aws_lambda 2.1).
