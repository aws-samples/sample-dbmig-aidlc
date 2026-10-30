# User-Defined Functions (UDFs)

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.udfs.html

**Conversion category:** Assisted (★★★ feature compatibility, ★★★★ automation)
**SCT automation:** Action code "Stored Procedures" — syntax and option differences.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected the side-effects row (DML allowed, DDL/COMMIT/dynamic SQL rejected — verified); binlog creation rule, DETERMINISTIC meaning, no UDFs in functional indexes, pipelined functions → JSON_TABLE/procedures.

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
| Side effects | Functions may run DML (not when called from SQL that queries the same table) | Functions may run DML (`MODIFIES SQL DATA`, verified) but **not DDL or `COMMIT`** (error 1422, verified), and no dynamic SQL (error 1336) | Move DDL/transaction control/dynamic SQL into procedures |

- Scalar UDF migration is mostly mechanical: remove `AS`, parenthesize/declare `RETURNS`, add characteristics.
- MySQL functions may modify data but not schema; a function that modifies a table cannot be called from a statement that reads or writes that same table (error 1442, verified).
- Characteristics are not enforced, but with binary logging on, creating a function that is not `DETERMINISTIC`, `NO SQL` or `READS SQL DATA` needs `log_bin_trust_function_creators = 1`. Declare `DETERMINISTIC` only when it is true — MySQL uses it for replication safety, not for result caching or index use.
- Functions cannot be used in functional indexes or generated columns (errors 3758 and 3763, verified).
- Pipelined/table functions (`PIPE ROW`, `TABLE(f(...))`) → a view, a procedure that returns a result set, or `JSON_TABLE` over a JSON value the function returns (MySQL 8).
- No parameter defaults, no overloading, no `%TYPE` (see `procedures-and-functions.md`).
- Table-valued functions have no equivalent — refactor to views or stored procedures + tables.
