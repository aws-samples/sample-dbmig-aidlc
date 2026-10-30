# DBMS_OUTPUT and PostgreSQL RAISE

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.raise.html

**Conversion category:** Manual (Three-star feature compatibility, no automation; different paradigm requires code rewrite)
**SCT automation:** No automation; SCT action code index N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): fixed the error-handling example (`INTO STRICT`), orafce `dbms_output` (verified), `RAISE_APPLICATION_ERROR` mapping.

## Oracle

`DBMS_OUTPUT` displays status/debug messages from PL/SQL. Requires `SET SERVEROUTPUT ON` to show on screen. `PUT`/`PUT_LINE` write to a buffer; `GET_LINE`/`GET_LINES` read it back.

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
    DBMS_OUTPUT.PUT_LINE ('The employee id is:' || v_jobid || ' and his last name is:' || v_lastname);
    EXIT WHEN c1%NOTFOUND;
  END LOOP;
  CLOSE c1;
END;
```

## PostgreSQL

Use `RAISE` as the alternative to `DBMS_OUTPUT`. Severity levels:

| Severity | Usage |
|---|---|
| `DEBUG1..DEBUG5` | Detailed developer info |
| `INFO` | Info explicitly requested by user |
| `NOTICE` | Info helpful to users (default `client_min_messages`) |
| `WARNING` | Likely problems (default `log_min_messages`) |
| `ERROR` | Aborts the current command |
| `LOG` | Admin info (e.g., checkpoints) |
| `FATAL` | Aborts the current session |
| `PANIC` | Aborts all sessions |

```sql
SET CLIENT_MIN_MESSAGES = 'debug';
-- Equivalent To Oracle SET SERVEROUTPUT ON

DO $$
BEGIN
  RAISE DEBUG USING MESSAGE := 'hello world';
END $$;
-- DEBUG: hello world
-- DO
```

Control visibility with `client_min_messages` (to client, default `NOTICE`) and `log_min_messages` (to server log, default `WARNING`).

## Summary — feature mapping

| Feature | Oracle | PostgreSQL |
|---|---|---|
| Disable output | `DISABLE` | Configure `client_min_messages`/`log_min_messages` |
| Enable output | `ENABLE` | Configure `client_min_messages`/`log_min_messages` |
| Get one line from buffer | `GET_LINE` | Store messages in an array/temp table to read elsewhere |
| Get array of lines | `GET_LINES` | Store messages in an array/temp table |
| Place line in buffer | `PUT_LINE` | `RAISE` |
| Most recent exception code | `SQLCODE + SQLERRM` | `SQLSTATE + SQLERRM` |

`PUT` + `NEW_LINE` (build a partial line) maps to concatenating into a varchar before raising:

```sql
-- Oracle
BEGIN
  DBMS_OUTPUT.PUT('1,'); DBMS_OUTPUT.PUT('2,');
  DBMS_OUTPUT.PUT('3,'); DBMS_OUTPUT.PUT('4');
  DBMS_OUTPUT.NEW_LINE();
END;
/

-- PostgreSQL
do $$
DECLARE message varchar := '';
begin
  message := concat(message,'1,');
  message := concat(message,'2,');
  message := concat(message,'3,');
  message := concat(message,'4,');
  RAISE NOTICE '%', message;
END$$;
```

Error message retrieval:

```sql
-- Oracle
DECLARE Name employees.last_name%TYPE;
BEGIN
  SELECT last_name INTO name FROM employees WHERE employee_id = -1;
EXCEPTION WHEN OTHERS THEN
  DBMS_OUTPUT.PUT_LINE(CONCAT('Error code ', SQLCODE,': ',sqlerrm));
END;
/

-- PostgreSQL (STRICT is required: without it, SELECT INTO returns NULL instead of raising NO_DATA_FOUND)
do $$
declare name employees.last_name%TYPE;
BEGIN
  SELECT last_name INTO STRICT name FROM employees WHERE employee_id = -1;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'Error code %: %', sqlstate, sqlerrm;   -- P0002: query returned no rows
end$$;
```

## Conversion notes

- Replace every `DBMS_OUTPUT.PUT_LINE(x)` with `RAISE NOTICE '%', x;` (or `RAISE DEBUG`/`INFO` as appropriate).
- Replace `SET SERVEROUTPUT ON` with `SET CLIENT_MIN_MESSAGES = 'debug'` (or matching level).
- `SQLCODE` (numeric) → `SQLSTATE` (5-char string) in PG; `SQLERRM` exists in both.
- No buffer/`GET_LINE` model in core PostgreSQL. Accumulate messages in a variable/array/temp table if downstream code reads them. **orafce** (available on Aurora 18) provides a `dbms_output` package with `enable`, `put`, `put_line`, `new_line`, `get_line`, `get_lines` (verified). Use it only when converted code really reads the buffer back. For plain debug output, `RAISE NOTICE` is the idiomatic choice.
- Messages raised with `RAISE` reach the client immediately (Oracle shows them only after the block ends) and are logged according to `log_min_messages`. Do not leave `RAISE NOTICE` in hot loops in production code.
- `RAISE EXCEPTION … USING ERRCODE = 'P0001', DETAIL = …, HINT = …` replaces `RAISE_APPLICATION_ERROR(-20001, msg)`. Map `-20xxx` numbers to custom SQLSTATEs (for example `'P2001'`) if callers check the number.
- `PUT` (partial line) → build a string and `RAISE` once.
