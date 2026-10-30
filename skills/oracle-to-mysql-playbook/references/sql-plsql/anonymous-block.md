# Anonymous Block

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.block.html

**Conversion category:** Assisted (★★★★ feature compatibility)
**SCT automation:** N/A — different syntax may require code rewrite.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Verified that compound blocks outside routines are still a syntax error on 3 / 8.4; temporary-procedure pattern, set-based rewrite, bind variables → user variables.

## Oracle

PL/SQL is a procedural extension of SQL. Code is divided into blocks using `DECLARE`, `BEGIN`, `EXCEPTION`, `END`. An **anonymous block** is unnamed PL/SQL code (not stored as a procedure/function/package) with three sections:
* **Declarative** (optional) — variables (names, types, initial values).
* **Executable** (mandatory) — at least one executable statement.
* **Exception-handling** (optional) — error handling.

```sql
-- Simple anonymous block
SET SERVEROUTPUT ON;
BEGIN
  DBMS_OUTPUT.PUT_LINE('hello world');
END;
/

-- Advanced: cursor + conditional logic + exception handling
SET SERVEROUTPUT ON;
DECLARE
  v_sal_chk        NUMBER;
  v_emp_work_years NUMBER;
  v_sql_cmd        VARCHAR2(2000);
BEGIN
  FOR v IN (SELECT EMPLOYEE_ID, FIRST_NAME||' '||LAST_NAME AS EMP_NAME, HIRE_DATE, SALARY
            FROM EMPLOYEES) LOOP
    v_emp_work_years := EXTRACT(YEAR FROM SYSDATE) - EXTRACT(YEAR FROM v.hire_date);
    IF v_emp_work_years >= 10 and v.salary <= 6000 then
      DBMS_OUTPUT.PUT_LINE('Consider a Bonus for: '||v.emp_name);
    END IF;
  END LOOP;
EXCEPTION WHEN OTHERS THEN
  DBMS_OUTPUT.PUT_LINE('CODE ERR: '||sqlerrm);
END;
/
```

## MySQL

Aurora MySQL has no direct anonymous-block construct. Achieve similar functionality with:
* `START TRANSACTION` … `COMMIT` for grouping statements, or
* A **stored procedure** for procedural logic (variables, cursors, conditionals, handlers).

See [Procedures and Functions](procedures-and-functions.md) and [Transaction Model](transaction-model.md).

## Conversion notes
- Wrap Oracle anonymous-block procedural logic in a temporary/permanent **stored procedure** and `CALL` it, since MySQL has no inline `BEGIN…END/` execution from the client like Oracle's `/`.
- Map `DBMS_OUTPUT.PUT_LINE` to `SELECT` (result output) — see DBMS_OUTPUT reference.
- Replace `EXCEPTION WHEN OTHERS` with MySQL `DECLARE … HANDLER` constructs inside the procedure.
- For simple multi-statement transactional logic, a `START TRANSACTION`/`COMMIT` block suffices.
- Still true on Aurora MySQL 3 and 8.4: a compound `BEGIN … END` (or MariaDB's `BEGIN NOT ATOMIC`) outside a routine is a syntax error (verified). Pattern for one-off scripts: `CREATE PROCEDURE tmp_x() BEGIN … END; CALL tmp_x(); DROP PROCEDURE tmp_x;` — needs `CREATE ROUTINE`, and with binary logging on also `log_bin_trust_function_creators` or `SUPER`-equivalent privileges.
- Anonymous blocks that only loop over rows are usually better as a single set-based statement (`INSERT … SELECT`, multi-table `UPDATE … JOIN`, or a CTE).
- Bind variables (`:x`) in SQL*Plus scripts → user variables (`SET @x = …`) in the client script.
