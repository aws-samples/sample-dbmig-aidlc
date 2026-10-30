# Procedures and Functions

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.stored.html

**Conversion category:** Assisted (Three-star feature compatibility, four-star automation; syntax/option differences, packages need redesign)
**SCT automation:** Four-star automation level; SCT action code index → Stored Procedures

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Oracle procedures → `CREATE PROCEDURE` (not `RETURNS VOID` functions); transaction-control rules incl. the silent COMMIT-inside-EXCEPTION loss (verified); packages aligned with the toolkit's `<package>_<subprogram>` convention; package state; SQL-standard bodies; SQLSTATE mapping.

## Oracle

PL/SQL stores reusable logic via `CREATE PROCEDURE` (performs DB actions) and `CREATE FUNCTION` (computes and returns a result). Privileges: `CREATE PROCEDURE` (own schema), `CREATE ANY PROCEDURE` (other schemas), `EXECUTE` (to run).

**Packages** group related procedures/functions: a **Package** (declaration) and a **Package Body** (executable code). Call with `EXEC PKG_EMP.CALCULTE_SAL('100');`.

Procedure example:

```sql
CREATE OR REPLACE PROCEDURE EMP_SAL_RAISE
(P_EMP_ID IN NUMBER, SAL_RAISE IN NUMBER)
AS
  V_EMP_CURRENT_SAL NUMBER;
BEGIN
  SELECT SALARY INTO V_EMP_CURRENT_SAL FROM EMPLOYEES WHERE EMPLOYEE_ID=P_EMP_ID;
  UPDATE EMPLOYEES SET SALARY=V_EMP_CURRENT_SAL+SAL_RAISE WHERE EMPLOYEE_ID=P_EMP_ID;
  DBMS_OUTPUT.PUT_LINE('New Salary For Employee ID: '||P_EMP_ID||' Is '||(V_EMP_CURRENT_SAL+SAL_RAISE));
EXCEPTION WHEN OTHERS THEN
  RAISE_APPLICATION_ERROR(-20001,'An error was encountered - '||SQLCODE||' -ERROR-'||SQLERRM);
  ROLLBACK;
  COMMIT;
END;
/
EXEC EMP_SAL_RAISE(200, 1000);
```

Function example:

```sql
CREATE OR REPLACE FUNCTION EMP_PERIOD_OF_SERVICE_YEAR (P_EMP_ID NUMBER)
RETURN NUMBER
AS
  V_PERIOD_OF_SERVICE_YEARS NUMBER;
BEGIN
  SELECT EXTRACT(YEAR FROM SYSDATE) - EXTRACT(YEAR FROM TO_DATE(HIRE_DATE))
  INTO V_PERIOD_OF_SERVICE_YEARS
  FROM EMPLOYEES WHERE EMPLOYEE_ID=P_EMP_ID;
  RETURN V_PERIOD_OF_SERVICE_YEARS;
END;
/
```

Package + body declared with `CREATE OR REPLACE PACKAGE` / `CREATE OR REPLACE PACKAGE BODY`, invoked as `EXEC PCK_CHINOOK_REPORTS.GET_ARTIST_BY_ALBUM('');`.

## PostgreSQL

> **Aurora PostgreSQL 18 guidance (supersedes the PG 13 advice in the original playbook).** Convert Oracle **procedures to `CREATE PROCEDURE`** and Oracle **functions to `CREATE FUNCTION`**. Procedures exist since PG 11, can `COMMIT`/`ROLLBACK`, and since PG 14 return `OUT` parameters through `CALL` (all verified on 18.6). The `RETURNS VOID` function examples below are kept for reference only. A function cannot commit, cannot be invoked with JDBC `{call …}` the same way, and changes the application's call shape.

PL/pgSQL is the main migration target language; PL/Tcl, PL/Perl and PL/v8 are also available in Aurora. List extensions with `show rds.extensions`. Privilege: `USAGE` on the language.

Procedure (recommended form for Oracle procedures):

```sql
CREATE OR REPLACE PROCEDURE emp_sal_raise(p_emp_id numeric, sal_raise numeric)
LANGUAGE plpgsql AS $$
DECLARE
  v_emp_current_sal numeric;
BEGIN
  SELECT salary INTO STRICT v_emp_current_sal FROM employees WHERE employee_id = p_emp_id;
  UPDATE employees SET salary = v_emp_current_sal + sal_raise WHERE employee_id = p_emp_id;
  RAISE NOTICE 'New salary for employee id % is %', p_emp_id, v_emp_current_sal + sal_raise;
EXCEPTION WHEN OTHERS THEN
  RAISE EXCEPTION 'An error was encountered - % -ERROR- %', SQLSTATE, SQLERRM
        USING ERRCODE = 'P2001';          -- custom code for Oracle -20001 (see notes)
END $$;

CALL emp_sal_raise(200, 1000);             -- Oracle: EXEC EMP_SAL_RAISE(200, 1000);
```

`OUT`/`INOUT` parameters, defaults and named notation (verified):

```sql
CREATE PROCEDURE p_args(IN a int, INOUT b int, OUT c text, d int DEFAULT 5) LANGUAGE plpgsql AS $$
BEGIN b := b + a + d; c := 'ok'; END $$;
CALL p_args(1, 10, NULL);                       -- returns one row: b=16, c='ok' (pass NULL for OUT args)
CALL p_args(a => 1, b => 10, c => NULL, d => 0); -- Oracle a => 1 named notation works unchanged
```

### Transaction control in procedures (verified on 18.6)

- `COMMIT`/`ROLLBACK` are allowed in a procedure (or `DO` block) only when it is called with `CALL` at top level, or from another procedure called that way. Called from a **function**, or inside an explicit transaction block, they fail with `2D000 invalid transaction termination`.
- **`COMMIT` is not allowed inside a `BEGIN … EXCEPTION … END` block** (`cannot commit while a subtransaction is active`). Worse, if that block has `WHEN OTHERS`, the handler **catches the commit error and the work is silently lost** (verified: the inserted row was gone and no error reached the caller). Put `COMMIT` outside any block that has an `EXCEPTION` clause, and wrap only the risky statements in inner blocks.
- Toolkit convention (`engines/oracle-to-postgresql/checks/non-portable-constructs.md`): prefer removing a trailing `COMMIT` and letting the caller own the transaction. Keep `COMMIT` only where the Oracle semantics require it (batch loops that commit every N rows).
- `PRAGMA AUTONOMOUS_TRANSACTION` has no equivalent. Options: `dblink_exec` over a loopback connection (`dblink` is available on Aurora 18) for audit/logging writes that must survive a rollback, or redesign (log via `RAISE LOG` / `pgaudit`, or let the caller log after rollback).

PL/pgSQL supports many Oracle PL/SQL elements (including `CREATE OR REPLACE PROCEDURE` syntax), making it the natural migration target.

Simple function:

```sql
CREATE OR REPLACE FUNCTION FUNC_ALG(P_NUM NUMERIC)
RETURNS NUMERIC
AS $$
BEGIN
  RETURN P_NUM * 2;
END; $$
LANGUAGE PLPGSQL;
```

`CREATE OR REPLACE` limits: can't change name, argument types, or return type; must own the function. Dollar-quoting (`$$ … $$`) avoids single-quote escaping. Use `LANGUAGE PLPGSQL`.

Legacy form (PG ≤ 10 and older AWS SCT output; **not** the recommended target on PG 18) — `EMP_SAL_RAISE` as a `RETURNS VOID` function:

```sql
CREATE OR REPLACE FUNCTION EMP_SAL_RAISE
(IN P_EMP_ID DOUBLE PRECISION, IN SAL_RAISE DOUBLE PRECISION)
RETURNS VOID
AS $$
DECLARE
  V_EMP_CURRENT_SAL DOUBLE PRECISION;
BEGIN
  SELECT SALARY INTO STRICT V_EMP_CURRENT_SAL FROM EMPLOYEES WHERE EMPLOYEE_ID = P_EMP_ID;
  UPDATE EMPLOYEES SET SALARY = V_EMP_CURRENT_SAL + SAL_RAISE WHERE EMPLOYEE_ID = P_EMP_ID;
  RAISE DEBUG USING MESSAGE := CONCAT_WS('', 'NEW SALARY FOR EMPLOYEE ID: ', P_EMP_ID, 'IS ', (V_EMP_CURRENT_SAL + SAL_RAISE));
EXCEPTION WHEN OTHERS THEN
  RAISE USING ERRCODE := '20001', MESSAGE := CONCAT_WS('', 'AN ERROR WAS ENCOUNTERED - ', SQLSTATE, ' -ERROR-', SQLERRM);
END; $$
LANGUAGE PLPGSQL;
select emp_sal_raise(200, 1000);
```

Converted `EMP_PERIOD_OF_SERVICE_YEAR`:

```sql
CREATE OR REPLACE FUNCTION EMP_PERIOD_OF_SERVICE_YEAR (IN P_EMP_ID DOUBLE PRECISION)
RETURNS DOUBLE PRECISION
AS $$
DECLARE
  V_PERIOD_OF_SERVICE_YEARS DOUBLE PRECISION;
BEGIN
  SELECT EXTRACT (YEAR FROM NOW()) - EXTRACT (YEAR FROM (HIRE_DATE))
  INTO STRICT V_PERIOD_OF_SERVICE_YEARS
  FROM EMPLOYEES WHERE EMPLOYEE_ID = P_EMP_ID;
  RETURN V_PERIOD_OF_SERVICE_YEARS;
END; $$
LANGUAGE PLPGSQL;
```

### Packages

PostgreSQL does NOT support packages/package bodies. Convert all package members to standalone procedures/functions.

- **This toolkit's convention is `<package>_<subprogram>`, lower-cased** (see `engines/oracle-to-postgresql/checks/package-naming.md`). `convert-code` checks it for collisions automatically. Use the names recorded in the conversion log.
- AWS SCT uses `package$member` instead; the example below shows SCT output.
- Alternative when the customer wants `pkg.proc(...)` call syntax preserved: **one schema per package** (`CREATE SCHEMA pkg; CREATE PROCEDURE pkg.proc(...)`). Choosing it overrides the toolkit convention, so record the decision in `customer-specific/decisions.md`.
- **Package variables** (state kept across calls in a session) have no equivalent. Use custom settings (`PERFORM set_config('pkg.var', v::text, false)` / `current_setting('pkg.var', true)`), a session temporary table, or redesign as parameters. Package initialization blocks become an explicit `pkg_init()` call. Session state also pins connections behind RDS Proxy/PgBouncer.
- **Package constants** → `IMMUTABLE` SQL functions (`CREATE FUNCTION pkg_c_max() RETURNS int LANGUAGE sql IMMUTABLE RETURN 100;`).
- **Overloads** convert directly: PostgreSQL overloads by argument types (verified).

AWS SCT-style example:

```sql
-- Oracle: EXEC PCK_CHINOOK_REPORTS.GET_ARTIST_BY_ALBUM('');
-- PostgreSQL (SCT):
SELECT PCK_CHINOOK_REPORTS$GET_ARTIST_BY_ALBUM('');

CREATE OR REPLACE FUNCTION
  chinook."PCK_CHINOOK_REPORTS$GET_ARTIST_BY_ALBUM" (p_artist_id text)
  RETURNS void LANGUAGE plpgsql
  AS $function$
  DECLARE V_ARTIST_NAME CHINOOK.ARTIST.NAME%TYPE;
  BEGIN
    SELECT art.name INTO STRICT V_ARTIST_NAME
    FROM chinook.album AS alb JOIN chinook.artist AS art USING (artistid)
    WHERE alb.title = p_artist_id;
    RAISE DEBUG USING MESSAGE := CONCAT_WS('', 'ArtistName: ', V_ARTIST_NAME);
  END;
  $function$;
```

Note the second converted package body uses `STRING_AGG` to replace Oracle `LISTAGG`.

### Other function features worth using on PG 18

- SQL-standard function bodies (PG 14+): `CREATE FUNCTION f(a int) RETURNS int LANGUAGE sql IMMUTABLE PARALLEL SAFE RETURN a * 2;` (verified). They are parsed at creation and dependency-tracked, so dropping a referenced table is blocked.
- Mark functions `IMMUTABLE`/`STABLE`/`VOLATILE` and `PARALLEL SAFE` correctly (Oracle `DETERMINISTIC` → `IMMUTABLE`, which is also required for expression indexes).
- `SECURITY DEFINER` (Oracle definer rights, the Oracle default `AUTHID DEFINER`) must be paired with `SET search_path = …` on the function to prevent search-path hijacking. PostgreSQL's default is invoker rights (`SECURITY INVOKER`, like `AUTHID CURRENT_USER`), so Oracle definer-rights routines that rely on the owner's privileges need `SECURITY DEFINER` added explicitly.

### Set-returning functions + LATERAL (PG 10+)

```sql
-- Previous
SELECT x, generate_series(1,5) AS g FROM tab;
-- New
SELECT id, g FROM emps, LATERAL generate_series(1,5) AS g;
```

## Conversion notes

- Convert Oracle **procedures** to `CREATE PROCEDURE` (called with `CALL`) and Oracle **functions** to `CREATE FUNCTION`. Converting procedures to `RETURNS VOID` functions is legacy (PG ≤ 10) advice. Keep the procedure/function distinction because application call sites depend on it (`engines/oracle-to-postgresql/app/app-sql-rules.md` §4).
- Use dollar-quoting `$$ … $$` and `LANGUAGE PLPGSQL`.
- `SELECT … INTO` → `SELECT … INTO STRICT` to mimic Oracle's NO_DATA_FOUND/TOO_MANY_ROWS behavior.
- `DBMS_OUTPUT.PUT_LINE` → `RAISE DEBUG/NOTICE`; `RAISE_APPLICATION_ERROR(-20001, msg)` → `RAISE EXCEPTION '%', msg USING ERRCODE = 'P2001'` (or the generic `'P0001'`). Avoid `ERRCODE '20001'`: it is accepted, but class `20` is the SQL-standard `case_not_found` class, so handlers and drivers misclassify it. Keep one consistent mapping table of `-20xxx` → custom SQLSTATE for the whole migration.
- `SQLCODE` → `SQLSTATE`. `LISTAGG` → `STRING_AGG`. `SYSDATE` → `LOCALTIMESTAMP(0)` / `NOW()`. `NUMBER` → `NUMERIC` (use `DOUBLE PRECISION` only for genuinely floating-point values; the SCT-style examples above use it, which can change results). `VARCHAR2` → `CHARACTER VARYING`.
- **Packages have no equivalent** — flatten to functions; SCT uses `pkg$member` naming.
- Remove `COMMIT`/`ROLLBACK` from anything converted to a **function**. In procedures they are allowed, with the restrictions in "Transaction control in procedures".
