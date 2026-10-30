# DBMS_SQL and PostgreSQL Dynamic Execution

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.dynamic.html

**Conversion category:** Manual (One-star feature compatibility, one-star automation; different paradigm and syntax require application and driver rewrite)
**SCT automation:** One-star automation level; SCT action code index N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): orafce `dbms_sql` subset (verified with `:name` binds), implicit result sets have no equivalent.

## Oracle

`DBMS_SQL` parses and runs dynamic SQL/DML/DDL with granular cursor control (open, parse, bind, execute, fetch, close).

```sql
DECLARE
  c1           INTEGER;
  rc1          SYS_REFCURSOR;
  n            NUMBER;
  first_name   VARCHAR2(50);
  last_name    VARCHAR2(50);
  email        VARCHAR2(50);
  phone_number VARCHAR2(50);
  job_title    VARCHAR2(50);
  start_date   DATE;
  end_date     DATE;
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
- `RETURN_RESULT` (12c) — returns a result set to the client without the caller knowing its shape.
- `TO_REFCURSOR` — convert a numeric DBMS_SQL cursor id to a ref cursor (after OPEN_CURSOR/PARSE/EXECUTE) to use native `FETCH`/`%NOTFOUND`.
- `TO_CURSOR_NUMBER` — convert a native dynamic SQL cursor to a numeric id manageable by DBMS_SQL.

## PostgreSQL

Core PostgreSQL has **no equivalent for `DBMS_SQL`** (no granular programmatic cursor control). You can still parse/run dynamic SQL.

**orafce `dbms_sql` (Aurora 18).** orafce implements a subset (`open_cursor`, `parse`, `bind_variable`, `define_column`, `execute`, `fetch_rows`, `column_value`, `close_cursor`). It uses Oracle-style `:name` placeholders. Verified on 18.6:
```sql
DO $$
DECLARE c int; n int; v text;
BEGIN
  c := dbms_sql.open_cursor();
  CALL dbms_sql.parse(c, 'select name from emp where id = :id');
  CALL dbms_sql.bind_variable(c, 'id', 1);
  CALL dbms_sql.define_column(c, 1, NULL::text);
  n := dbms_sql.execute(c);
  IF dbms_sql.fetch_rows(c) > 0 THEN CALL dbms_sql.column_value(c, 1, v); END IF;
  CALL dbms_sql.close_cursor(c);
END $$;
```
Note the procedure calls use `CALL`. The full orafce function list on Aurora 18.6 is `bind_array`, `bind_variable`, `close_cursor`, `column_value`, `define_array`, `define_column`, `describe_columns`, `execute`, `execute_and_fetch`, `fetch_rows`, `is_open`, `last_row_count`, `open_cursor`, `parse` (plus `_f` function variants and `debug_cursor`). Array binds cover many `FORALL`-style uses. `GET_NEXT_RESULT`, `RETURN_RESULT`, `TO_REFCURSOR` and `TO_CURSOR_NUMBER` are not provided. Use it for mechanical conversion of heavy `DBMS_SQL` code; prefer native `EXECUTE` for new or rewritten code.

Dynamic cursor with `FOR … IN SELECT`:

```sql
CREATE OR REPLACE FUNCTION GetErrors ()
RETURNS VARCHAR
AS
$$
DECLARE
  _currow RECORD;
  msg VARCHAR(200);
  TITLE VARCHAR(10);
  CODE_NUM VARCHAR(10);
BEGIN
  msg := '';
  FOR _currow IN SELECT TITLE, CODE_NUM, count(*) FROM A group by TITLE,CODE_NUM
  LOOP
    TITLE := _currow.TITLE;
    CODE_NUM := _currow.CODE_NUM;
    msg := msg||rpad(TITLE,20)||rpad(CODE_NUM,20);
  END LOOP;
  RETURN msg;
END;
$$ LANGUAGE plpgsql;
```

Open a refcursor for a dynamic statement via `EXECUTE`:

```sql
CREATE OR REPLACE FUNCTION GetErrors () RETURNS VARCHAR AS $$
declare
  refcur refcursor;
  c_id integer;
  title varchar (10);
  code_num varchar (10);
  alert_mesg VARCHAR(1000) := '';
BEGIN
  OPEN refcur FOR execute('select * from Errors');
  loop
    fetch refcur into title, code_num;
    if not found then exit; end if;
    alert_mesg := alert_mesg||rpad(title,20)||rpad(code_num,20);
  end loop;
  close refcur;
  return alert_mesg;
END;
$$ LANGUAGE plpgsql;
```

## Conversion notes

- Core PostgreSQL has no analog to the `DBMS_SQL` open/parse/bind/execute/fetch API. Either use orafce `dbms_sql` (subset, Aurora-available) or redesign the dynamic SQL with `EXECUTE … USING`.
- Oracle 12c **implicit result sets** (`DBMS_SQL.RETURN_RESULT`) have no PostgreSQL equivalent. Return `refcursor` values as `INOUT` parameters of a procedure, or use a set-returning function.
- Use `EXECUTE 'sql' USING params` (PL/pgSQL) for parametrized dynamic statements, or `OPEN refcur FOR EXECUTE format(...) USING ...` for dynamic cursors.
- For dynamic identifiers (table/column names), use `format()` with `%I` (identifier) / `%L` (literal) to avoid SQL injection.
- `PREPARE`/`EXECUTE`/`DEALLOCATE` (SQL-level) handle reusable prepared statements.
- Oracle `SYS_REFCURSOR` → PG `refcursor`; returning result sets to clients differs and usually requires driver/application changes.
