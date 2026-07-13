# User-Defined Functions (UDFs)

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.udfs.html

**Conversion category:** Assisted (★★★ feature compatibility, ★★★★ automation)
**SCT automation:** Action code "Stored Procedures" — syntax and option differences.

## Oracle

Oracle UDFs (PL/SQL, Java, or C) provide functionality beyond built-in SQL functions and can appear wherever built-in functions can: scalar return in `SELECT`, DML, and `WHERE`/`GROUP BY`/`ORDER BY`/`HAVING`/`CONNECT BY`/`START WITH`.

```sql
CREATE OR REPLACE FUNCTION TOTAL_EMP_SAL_BY_YEARS (p_hire_date DATE, p_current_sal NUMBER)
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

## MySQL

Aurora MySQL supports **scalar UDFs only** — no table-valued functions. Stored functions **cannot** contain explicit transaction statements (`COMMIT`/`ROLLBACK`). Characteristics (saved with the definition, shown via `SHOW CREATE FUNCTION`):
* `DETERMINISTIC` must be explicitly stated (engine assumes non-deterministic otherwise; MySQL does not validate the claim).
* `CONTAINS SQL` — no data read/modify statements.
* `READS SQL DATA` — reads (e.g., `SELECT`) but no modify.
* `MODIFIES SQL DATA` — may modify data.
  (These are advisory only; the server doesn't enforce them.)

```sql
-- Syntax
CREATE FUNCTION <Function Name> ([<Function Parameter>[,...]])
RETURNS <Returned Data Type> [characteristic ...]
<Function Code Body>
  characteristic: COMMENT '<Comment>' | LANGUAGE SQL | [NOT] DETERMINISTIC
    | { CONTAINS SQL | NO SQL | READS SQL DATA | MODIFIES SQL DATA }
    | SQL SECURITY { DEFINER | INVOKER }

-- Scalar function: uppercase first character
CREATE FUNCTION UpperCaseFirstChar (String VARCHAR(20))
RETURNS VARCHAR(20)
BEGIN
  RETURN CONCAT(UPPER(LEFT(String, 1)), LOWER(SUBSTRING(String, 2, 19)));
END

SELECT UpperCaseFirstChar('mIxEdCasE');   -- Mixedcase
```

## Conversion notes

| Oracle | Aurora MySQL | Comment |
|---|---|---|
| Scalar UDF | Scalar UDF | `CREATE FUNCTION`, similar syntax — **remove the `AS` keyword** |
| Inline table-valued UDF | N/A | Use views; replace parameters with `WHERE` filter predicates |
| Multi-statement table-valued UDF | N/A | Use stored procedures to populate tables, then read from the table |
| Determinism implicit | Explicit declaration | State `DETERMINISTIC` to enable engine optimizations |
| UDF boundaries local only | Can change data and schema | MySQL rules are more lenient — avoid unexpected side effects |

- Scalar UDF migration is mostly mechanical: remove `AS`, parenthesize/declare `RETURNS`, add characteristics.
- MySQL functions may modify data/schema (Oracle doesn't) — be careful of side effects in function calls.
- Table-valued functions have no equivalent — refactor to views or stored procedures + tables.
