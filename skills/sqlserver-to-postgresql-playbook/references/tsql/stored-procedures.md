# Stored Procedures

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.storedprocedures.html

**Conversion category:** Assisted (three-star feature compatibility, four-star automation)
**SCT automation:** Four-star automation level; SCT action code index: Stored Procedures

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): CREATE PROCEDURE is now the default (CALL, INOUT/OUT, COMMIT), with RETURNS TABLE functions only for result-set procedures and refcursors for multiple result sets; TVP→composite array/jsonb, RECOMPILE→plan_cache_mode, BULK INSERT→client COPY/aws_s3; all patterns verified on 18.6.

## SQL Server

Stored procedures are persisted code modules run via `EXECUTE`, with multiple `IN`/`OUT` parameters (`IN` is default; `OUT` explicit; can be both). Table-valued user-defined types can be input parameters. Options: `EXECUTE AS` (security context), `RECOMPILE`, `ENCRYPTION`. A procedure can feed an `INSERT` (only the first returned row is evaluated).

Syntax:

```sql
CREATE [ OR ALTER ] { PROC | PROCEDURE } <Procedure Name>
[<Parameter List>
[ WITH [ ENCRYPTION ]|[ RECOMPILE ]|[ EXECUTE AS ...]]
AS {
[ BEGIN ]
<SQL Code Body>
[ END ] }[;]
```

Example — parameterized procedure with OUT:

```sql
CREATE PROCEDURE ValidateEmail
@Email VARCHAR(128), @IsValid BIT = 0 OUT
AS
BEGIN
IF @Email LIKE N'%@%' SET @IsValid = 1
ELSE SET @IsValid = 0
RETURN @IsValid
END;

DECLARE @IsValid BIT
EXECUTE [ValidateEmail] @Email = 'X@y.com', @IsValid = @IsValid OUT;
SELECT @IsValid; -- Returns 1
```

Example — RETURN to pass an error value:

```sql
CREATE PROCEDURE ProcessImportBatch @BatchID INT
AS
BEGIN
BEGIN TRY
EXECUTE Step1 @BatchID
EXECUTE Step2 @BatchID
EXECUTE Step3 @BatchID
END TRY
BEGIN CATCH
IF ERROR_NUMBER() = 235
RETURN -1 -- indicate special condition
ELSE
THROW -- handle error normally
END CATCH
END
```

Table-valued input parameter:

```sql
CREATE TYPE OrderItems AS TABLE
( OrderID INT NOT NULL, Item VARCHAR(20) NOT NULL, Quantity SMALLINT NOT NULL,
  PRIMARY KEY(OrderID, Item) );

CREATE PROCEDURE InsertOrderItems
@OrderItems AS OrderItems READONLY
AS
BEGIN
  INSERT INTO OrderItems(OrderID, Item, Quantity)
  SELECT OrderID, Item, Quantity FROM @OrderItems
END;
```

INSERT…EXEC:

```sql
INSERT INTO <MyTable> EXECUTE <MyStoredProcedure>;
```

## PostgreSQL

Aurora PostgreSQL 18 has both `CREATE PROCEDURE` (PG 11+, invoked with `CALL`, may `COMMIT`/`ROLLBACK`, `OUT` parameters since PG 14) and `CREATE FUNCTION` (invoked in `SELECT`, returns a value or a set). The original playbook (PostgreSQL 10) converted every procedure to a function; that is no longer the recommendation. Main language for migrating T-SQL is **PL/pgSQL**; PL/Perl, PL/Tcl and PL/v8 are also available (PL/Python is not). List Aurora extensions with `SHOW rds.extensions`. The user needs `USAGE` privilege on the language.

**Which object to create (toolkit convention):**

| T-SQL procedure shape | PostgreSQL 18 target | Caller change |
|---|---|---|
| DML / logic, `OUTPUT` params, `RETURN <int>` status | `CREATE PROCEDURE p(IN …, INOUT …, OUT …)` | `EXEC p @a, @b OUT` → `CALL p(a, NULL)`; read OUT values from the result row |
| Body ends in a bare `SELECT` (result set) | `CREATE FUNCTION f(…) RETURNS TABLE (…)` | `EXEC p` → `SELECT * FROM f(…)` (see `engines/sqlserver-to-postgresql/checks/non-portable-constructs.md` §5) |
| Several result sets | `CREATE PROCEDURE p(…, INOUT rc1 refcursor, INOUT rc2 refcursor)` | caller calls, then `FETCH ALL FROM rc1` in the same transaction |
| Manages its own transactions | `CREATE PROCEDURE` (functions cannot `COMMIT`) | must be `CALL`ed outside an explicit transaction block |

Verified on Aurora PostgreSQL 18.6:

```sql
-- SQL Server: CREATE PROCEDURE ValidateEmail @Email VARCHAR(128), @IsValid BIT = 0 OUT … RETURN @IsValid
CREATE OR REPLACE PROCEDURE validate_email(p_email varchar, INOUT p_isvalid boolean DEFAULT false)
LANGUAGE plpgsql AS $$
BEGIN
  p_isvalid := p_email LIKE '%@%';
END $$;

CALL validate_email('x@y.com', NULL);                   -- returns one row: p_isvalid = true
CALL validate_email(p_email => 'nope', p_isvalid => NULL); -- named notation replaces @Email = …

-- inside PL/pgSQL an OUT/INOUT argument must be a variable:
--   CALL validate_email(v_email, v_valid);
```

- `RETURN @status` (integer status code) has no equivalent in a procedure: add an `INOUT p_status int` parameter, or raise an exception for error statuses.
- A procedure that `COMMIT`s keeps the committed work even if later statements roll back (verified: `INSERT 1; COMMIT; INSERT 2; ROLLBACK` leaves row 1).
- `WITH EXECUTE AS OWNER` → `SECURITY DEFINER` **plus** `SET search_path = pg_catalog, <schema>` on the routine, so a caller cannot hijack unqualified names.

Example — simple function:

```sql
CREATE OR REPLACE FUNCTION FUNC_ALG(P_NUM NUMERIC)
RETURNS NUMERIC
AS $$
BEGIN
  RETURN P_NUM * 2;
END; $$
LANGUAGE PLPGSQL;
```
`CREATE OR REPLACE` cannot change function name, argument types, or return type; user must own the function. `$$` dollar-quoting avoids escaping single quotes.

Example — with exception handling:

Original playbook example, kept for reference. Today write it as `CREATE PROCEDURE emp_sal_raise(p_emp_id integer, sal_raise numeric)` with `CALL emp_sal_raise(200, 1000)`, use `numeric` rather than `DOUBLE PRECISION` for money (toolkit datatype map), and use a custom SQLSTATE such as `P0001` rather than `'20001'` (see `error-handling.md`):

```sql
CREATE OR REPLACE FUNCTION EMP_SAL_RAISE
(IN P_EMP_ID DOUBLE PRECISION, IN SAL_RAISE DOUBLE PRECISION)
RETURNS VOID
AS $$
DECLARE
V_EMP_CURRENT_SAL DOUBLE PRECISION;
BEGIN
SELECT SALARY INTO STRICT V_EMP_CURRENT_SAL
FROM EMPLOYEES WHERE EMPLOYEE_ID = P_EMP_ID;
UPDATE EMPLOYEES SET SALARY = V_EMP_CURRENT_SAL + SAL_RAISE WHERE EMPLOYEE_ID = P_EMP_ID;
RAISE DEBUG USING MESSAGE := CONCAT_WS('', 'NEW SALARY FOR EMPLOYEE ID: ', P_EMP_ID, ' IS ', (V_EMP_CURRENT_SAL + SAL_RAISE));
EXCEPTION
WHEN OTHERS THEN
RAISE USING ERRCODE := '20001', MESSAGE := CONCAT_WS('', 'AN ERROR WAS ENCOUNTERED -', SQLSTATE, ' -ERROR-', SQLERRM);
END; $$
LANGUAGE PLPGSQL;

select emp_sal_raise(200, 1000);
```

Set-returning functions and `LATERAL` (PostgreSQL 10+):

```sql
SELECT id, g FROM emps, LATERAL generate_series(1,5) AS g;
```

## Summary

| Feature | SQL Server | Aurora PostgreSQL | Workaround |
|---|---|---|---|
| CREATE syntax | `CREATE PROC\|PROCEDURE name @Param ... AS <Body>` | `CREATE [OR REPLACE] PROCEDURE name(Param <Type>,...) LANGUAGE plpgsql AS $$ <body> $$` | Keep `PROCEDURE` (use `FUNCTION … RETURNS TABLE` only for result-set procedures); drop `@`; wrap params in parentheses; `CREATE OR ALTER` → `CREATE OR REPLACE` (cannot change parameter types — drop and recreate) |
| Security context | `EXEC AS { CALLER\|SELF\|OWNER\|'user' }` | `SECURITY INVOKER \| SECURITY DEFINER` | `EXECUTE AS user`/`SELF` → `SECURITY DEFINER`; `CALLER` → `SECURITY INVOKER` |
| Encryption | `WITH ENCRYPTION` | Not supported | — |
| Parameter direction | `IN`, `OUT\|OUTPUT` | `IN`, `OUT`, `INOUT`, `VARIADIC` | `OUTPUT`→`OUT`; bidirectional `OUT`→`INOUT` |
| Recompile | `WITH RECOMPILE` | Not needed as a routine option | `plan_cache_mode = force_custom_plan` set on the routine (`ALTER PROCEDURE … SET plan_cache_mode = force_custom_plan`) |
| Table-valued parameters | `READONLY` table type | **No table-valued parameters** | array of a composite type (`p_items orderitem[]` + `unnest`) or `jsonb` + `jsonb_populate_recordset` (both verified); caller contract changes |
| Bulk load | `BULK INSERT` | Not in SQL (server-file `COPY` is not allowed on Aurora) | client-side `COPY … FROM STDIN` / `\copy`, or `aws_s3.table_import_from_s3` |
| `INSERT … EXEC` | supported | not supported | `INSERT INTO t SELECT * FROM f(…)` with a `RETURNS TABLE` function |

## Conversion notes
- Convert T-SQL procedures to PostgreSQL `CREATE PROCEDURE` (invoked with `CALL`); only result-set procedures become `RETURNS TABLE` functions. `SET NOCOUNT ON` is dropped.
- Remove `@` from parameter names; wrap parameter list in parentheses; use `$$` dollar-quoting for the body.
- `EXECUTE AS` → `SECURITY DEFINER`/`SECURITY INVOKER`.
- No `WITH ENCRYPTION` equivalent (source is visible in `pg_proc.prosrc` to anyone who can connect; restrict with privileges). `WITH RECOMPILE` → `SET plan_cache_mode = force_custom_plan` on the routine.
- Table-valued parameters → composite-type array or `jsonb` parameter (see `engines/sqlserver-to-postgresql/checks/non-portable-constructs.md` §15).
- `OUTPUT` → `OUT`; bidirectional parameters → `INOUT`.
- `INSERT ... EXEC` has no direct equivalent — use a function returning a set with `INSERT ... SELECT * FROM func()`.
