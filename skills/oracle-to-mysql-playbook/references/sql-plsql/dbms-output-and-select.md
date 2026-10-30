# DBMS_OUTPUT and SELECT

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.raise.html

**Conversion category:** Manual (★★★ feature compatibility, no automation)
**SCT automation:** Action code "DBMS_OUTPUT" — different paradigm/syntax requires application and driver rewrite.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Result-set semantics (multiple result sets; Data API returns only the first — verified), aliasing instead of double quotes (ANSI_QUOTES), log-table and SIGNAL warning alternatives.

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

> Note: give each message a column alias (`SELECT 'OUTPUT: Before count' AS msg`) rather than relying on double-quoted strings: if `ANSI_QUOTES` is in `sql_mode`, `"…"` is an identifier, not a string.

Each `SELECT` in a procedure returns a **separate result set**. Clients must read all of them (JDBC `getMoreResults()`, PyMySQL `cursor.nextset()`); some tools, including the RDS Data API, return only the first result set (verified: the Data API returned only `OUTPUT: Before count`).

## Conversion notes
- No buffered-message equivalent — replace `DBMS_OUTPUT.PUT_LINE` with `SELECT '<message>'`.
- Output is returned as a result set, not a screen buffer — application/driver code that read `DBMS_OUTPUT` must be rewritten to consume result sets.
- No equivalent for `GET_LINE`/`GET_LINES` buffer retrieval — restructure logic to write to a table or return result sets.
- Use `SELECT ... INTO var` for assignments and `SELECT CONCAT(...)` to format messages.
- For diagnostic output that must not change the procedure's result sets, write to a log table (`INSERT INTO app_log(ts, msg) VALUES (NOW(6), …)`) or use `SIGNAL SQLSTATE '01000' SET MESSAGE_TEXT = …` to raise a **warning** the client can read with `SHOW WARNINGS`.
- Remove debug `DBMS_OUTPUT` calls entirely where possible; extra result sets break callers that expect exactly one.
