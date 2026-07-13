# Procedures and Functions

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.stored.html

**Conversion category:** Assisted (Three-star feature compatibility, four-star automation; syntax/option differences, packages need redesign)
**SCT automation:** Four-star automation level; SCT action code index → Stored Procedures

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

PostgreSQL (this playbook's version, PG 13) implements both procedures and functions via **`CREATE FUNCTION`** — `CREATE PROCEDURE` is noted as not compatible here. PL/pgSQL is the main migration target language; PL/Tcl and PL/Perl are also available in Aurora. List extensions with `show rds.extensions`. Privilege: `USAGE` on the language.

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

Converted `EMP_SAL_RAISE` (procedure → `RETURNS VOID` function):

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

PostgreSQL does NOT support packages/package bodies. Convert all package members to standalone functions. AWS SCT names converted functions as `package$member` using a `$` separator:

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

### Set-returning functions + LATERAL (PG 10+)

```sql
-- Previous
SELECT x, generate_series(1,5) AS g FROM tab;
-- New
SELECT id, g FROM emps, LATERAL generate_series(1,5) AS g;
```

## Conversion notes

- Convert Oracle **procedures** to PG functions `RETURNS VOID` (this playbook targets PG 13's `CREATE FUNCTION`). `CALL`/`CREATE PROCEDURE` exists in later PG versions — check your Aurora engine version.
- Use dollar-quoting `$$ … $$` and `LANGUAGE PLPGSQL`.
- `SELECT … INTO` → `SELECT … INTO STRICT` to mimic Oracle's NO_DATA_FOUND/TOO_MANY_ROWS behavior.
- `DBMS_OUTPUT.PUT_LINE` → `RAISE DEBUG/NOTICE`; `RAISE_APPLICATION_ERROR(-20001, msg)` → `RAISE USING ERRCODE := '20001', MESSAGE := …`.
- `SQLCODE` → `SQLSTATE`. `LISTAGG` → `STRING_AGG`. `SYSDATE` → `NOW()`. `NUMBER` → `DOUBLE PRECISION`/`NUMERIC`. `VARCHAR2` → `CHARACTER VARYING`.
- **Packages have no equivalent** — flatten to functions; SCT uses `pkg$member` naming.
- Remove Oracle-specific `COMMIT`/`ROLLBACK` patterns inside functions (transaction control is restricted in functions).
