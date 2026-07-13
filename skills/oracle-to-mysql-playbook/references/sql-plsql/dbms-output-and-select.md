# DBMS_OUTPUT and SELECT

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.raise.html

**Conversion category:** Manual (★★★ feature compatibility, no automation)
**SCT automation:** Action code "DBMS_OUTPUT" — different paradigm/syntax requires application and driver rewrite.

## Oracle

`DBMS_OUTPUT` sends messages from procedures, functions, and anonymous blocks to a message buffer — typically for debugging/display. Requires `SET SERVEROUTPUT ON` to show on screen.

```sql
SET SERVEROUTPUT ON
DECLARE
  CURSOR c1 IS
    SELECT last_name, job_id FROM employees
    WHERE REGEXP_LIKE (job_id, 'S[HT]_CLERK')
    ORDER BY last_name;
  v_lastname employees.last_name%TYPE;
  v_jobid employees.job_id%TYPE;
BEGIN
  OPEN c1;
  LOOP
    FETCH c1 INTO v_lastname, v_jobid;
    DBMS_OUTPUT.PUT_LINE('The employee id is:' || v_jobid || ' and his last name is:' || v_lastname);
    EXIT WHEN c1%NOTFOUND;
  END LOOP;
  CLOSE c1;
END;
```

`PUT`/`PUT_LINE` can also buffer information read later by another procedure via `GET_LINE`/`GET_LINES`.

## MySQL

Use `SELECT` to display output messages in Aurora MySQL.

```sql
delimiter //
CREATE PROCEDURE emp_counter (param1 INTEGER)
BEGIN
  SELECT "" 'OUTPUT: Before count';
  SELECT COUNT(*) INTO param1 FROM EMPS;
  SELECT concat('Employees count: ', param1) as '';
  SELECT "" 'OUTPUT: After count';
END//
delimiter ;

call emp_counter(1);
-- OUTPUT: Before count
-- Employees count: 8
-- OUTPUT: After count
```

> Note: Use double quotation marks with `SELECT` for cleaner display; otherwise messages appear twice (as both header and value).

## Conversion notes
- No buffered-message equivalent — replace `DBMS_OUTPUT.PUT_LINE` with `SELECT '<message>'`.
- Output is returned as a result set, not a screen buffer — application/driver code that read `DBMS_OUTPUT` must be rewritten to consume result sets.
- No equivalent for `GET_LINE`/`GET_LINES` buffer retrieval — restructure logic to write to a table or return result sets.
- Use `SELECT ... INTO var` for assignments and `SELECT CONCAT(...)` to format messages.
