# DBMS_SQL

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.dynamic.html

**Conversion category:** Manual (★ feature compatibility, ★ automation)
**SCT automation:** N/A — different paradigm/syntax requires application and driver rewrite.

## Oracle

`DBMS_SQL` parses and runs dynamic SQL, DML, and DDL (usually from a PL/SQL package/procedure/function) with granular cursor control. Flow: `OPEN_CURSOR` → `PARSE` → `BIND_VARIABLE` → `EXECUTE` → `GET_NEXT_RESULT`/`FETCH` → `CLOSE_CURSOR`.

```sql
DECLARE
  c1 INTEGER;
  rc1 SYS_REFCURSOR;
  n NUMBER;
  first_name VARCHAR2(50); last_name VARCHAR2(50);
  email VARCHAR2(50); phone_number VARCHAR2(50);
  job_title VARCHAR2(50); start_date DATE; end_date DATE;
BEGIN
  c1 := DBMS_SQL.OPEN_CURSOR(true);
  DBMS_SQL.PARSE(c1, 'BEGIN emp_info(:id); END;', DBMS_SQL.NATIVE);
  DBMS_SQL.BIND_VARIABLE(c1, ':id', 176);
  n := DBMS_SQL.EXECUTE(c1);
  DBMS_SQL.GET_NEXT_RESULT(c1, rc1);
  FETCH rc1 INTO first_name, last_name, email, phone_number;
  DBMS_SQL.GET_NEXT_RESULT(c1, rc1);
  LOOP
    FETCH rc1 INTO job_title, start_date, end_date;
    EXIT WHEN rc1%NOTFOUND;
  END LOOP;
  DBMS_SQL.CLOSE_CURSOR(c1);
END;
/
```

Additional procedures:
* `RETURN_RESULT` — returns a result set to the client (Oracle 12c; common with SQL*Plus) without the invoker needing to know its structure.
* `TO_REFCURSOR` — converts a `DBMS_SQL` numeric cursor ID to a ref cursor (after `OPEN_CURSOR`/`PARSE`/`EXECUTE`) so you can use native `FETCH`/`%NOTFOUND`.
* `TO_CURSOR_NUMBER` — converts a native dynamic-SQL cursor to a `DBMS_SQL` numeric cursor ID for `DBMS_SQL` management.

## MySQL

No `DBMS_SQL` equivalent. Aurora MySQL options:
* Stored procedures or functions.
* `PREPARE` and `EXECUTE` (prepared statements).

## Conversion notes
- Replace the `DBMS_SQL` open/parse/bind/execute/fetch flow with `PREPARE`/`EXECUTE` plus stored-procedure cursors.
- MySQL prepared statements bind only data values (`?` placeholders) — for dynamic identifiers, build the SQL string with `CONCAT` before `PREPARE`.
- No equivalent for `RETURN_RESULT`/`TO_REFCURSOR`/`TO_CURSOR_NUMBER` — restructure to return result sets directly from a procedure or use server-side cursors.
- This is a low-compatibility area: expect application and driver code changes, not just SQL rewrites.
