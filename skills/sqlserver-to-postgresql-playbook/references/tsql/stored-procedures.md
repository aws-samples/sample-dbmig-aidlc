# Stored Procedures

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.storedprocedures.html

**Conversion category:** Assisted (three-star feature compatibility, four-star automation)
**SCT automation:** Four-star automation level; SCT action code index: Stored Procedures

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

PostgreSQL 10 supports stored functions via `CREATE FUNCTION` (in this playbook context, `CREATE PROCEDURE` is treated as not supported — use `CREATE FUNCTION`). Main language for migrating T-SQL is **PL/pgSQL**; PL/Tcl and PL/Perl also available. Use `show.rds.extensions` to list Aurora extensions. The user needs `USAGE` privilege on the language.

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
| CREATE syntax | `CREATE PROC\|PROCEDURE name @Param ... AS <Body>` | `CREATE [OR REPLACE] FUNCTION name(Param <Type>,...) AS $$ <body>` | Use `FUNCTION` not `PROC`; drop `@` from params; wrap params in parentheses; use `$$` body |
| Security context | `EXEC AS { CALLER\|SELF\|OWNER\|'user' }` | `SECURITY INVOKER \| SECURITY DEFINER` | `EXECUTE AS user`/`SELF` → `SECURITY DEFINER`; `CALLER` → `SECURITY INVOKER` |
| Encryption | `WITH ENCRYPTION` | Not supported | — |
| Parameter direction | `IN`, `OUT\|OUTPUT` | `IN`, `OUT`, `INOUT`, `VARIADIC` | `OUTPUT`→`OUT`; bidirectional `OUT`→`INOUT` |
| Recompile | `WITH RECOMPILE` | Not supported | — |
| Table-valued parameters | declared table type | declared table type | — |
| Bulk load | `BULK INSERT` | Not supported | — |

## Conversion notes
- Convert `CREATE PROCEDURE` to `CREATE FUNCTION`; T-SQL procedures generally become PL/pgSQL functions.
- Remove `@` from parameter names; wrap parameter list in parentheses; use `$$` dollar-quoting for the body.
- `EXECUTE AS` → `SECURITY DEFINER`/`SECURITY INVOKER`.
- No `WITH ENCRYPTION`, `WITH RECOMPILE`, or `BULK INSERT` equivalents.
- `OUTPUT` → `OUT`; bidirectional parameters → `INOUT`.
- `INSERT ... EXEC` has no direct equivalent — use a function returning a set with `INSERT ... SELECT * FROM func()`.
