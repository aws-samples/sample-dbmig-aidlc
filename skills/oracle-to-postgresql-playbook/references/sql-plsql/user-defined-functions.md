# User-Defined Functions (UDFs)

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.udfs.html

**Conversion category:** Assisted (Three-star feature compatibility, four-star automation; syntax/option differences)
**SCT automation:** Four-star automation level; SCT action code index → Stored Procedures

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
- `SYSDATE` → `NOW()`.
- Dollar-quote the body (`$$ … $$` or named `$BODY$ … $BODY$`) and add `LANGUAGE PLPGSQL`.
- UDFs can still be used inline in queries as in Oracle.
- Oracle UDFs in Java/C require full reimplementation (PL/Python, PL/Perl, or C extensions in Aurora where available).
