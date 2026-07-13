# Stored procedures for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.storedprocedures.html

**Conversion category:** Assisted (Three star feature compatibility)
**SCT automation:** Four star automation level

## SQL Server

Stored procedures are persisted code modules run via `EXECUTE`. Multiple IN/OUT parameters; table-valued user-defined types allowed as input. `IN` is default direction; `OUT` must be explicit. Can run under any security context via `EXECUTE AS`, recompile via `RECOMPILE`, and encrypt via `ENCRYPTION`. Can serve as input to an `INSERT` (only first row evaluated). Supports a default integer output via `RETURN`, retrievable with `EXEC @Parameter = <proc>`.

### Syntax

```sql
CREATE [ OR ALTER ] { PROC | PROCEDURE } <Procedure Name>
[<Parameter List>
[ WITH [ ENCRYPTION ]|[ RECOMPILE ]|[ EXECUTE AS ...]]
AS {
[ BEGIN ]
<SQL Code Body>
[RETURN [<Integer Value>]]
[ END ] }[;]
```

### Examples

```sql
CREATE PROCEDURE ValidateEmail
@Email VARCHAR(128), @IsValid BIT = 0 OUT
AS
BEGIN
IF @Email LIKE N'%@%'
    SET @IsValid = 1
ELSE
    SET @IsValid = 0
RETURN
END;

DECLARE @IsValid BIT
EXECUTE [ValidateEmail]
    @Email = 'X@y.com', @IsValid = @IsValid OUT;
SELECT @IsValid;  -- Returns 1

-- RETURN to pass an error value
CREATE PROCEDURE ProcessImportBatch
@BatchID INT
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

-- Table-valued input parameter
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

-- INSERT...EXEC
INSERT INTO <MyTable>
EXECUTE <MyStoredProcedure>;
```

## MySQL

Aurora MySQL stored procedures offer similar functionality, supporting security run context and IN/OUT/INOUT parameters. Stored procedures, triggers, and UDFs are collectively *stored routines*. With binary logging enabled, `SUPER` privilege is required to run stored routines — or set `log_bin_trust_function_creators` = true in the DB parameter group. Routines may contain control flow, DML, DDL, and transaction management (`START TRANSACTION`, `COMMIT`, `ROLLBACK`).

### Syntax

```sql
CREATE [DEFINER = { user | CURRENT_USER }] PROCEDURE sp_name
([ IN | OUT | INOUT ] <Parameter> <Parameter Data Type> ... )
COMMENT 'string' |
LANGUAGE SQL |
[NOT] DETERMINISTIC |
{ CONTAINS SQL | NO SQL | READS SQL DATA | MODIFIES SQL DATA } |
SQL SECURITY { DEFINER | INVOKER }
<Stored Procedure Code Body>
```

### Examples

```sql
-- Replace RETURN value with OUT parameter
CREATE PROCEDURE ProcessImportBatch()
IN @BatchID INT, OUT @ErrorNumber INT
BEGIN
    CALL Step1 (@BatchID)
    CALL Step2 (@BatchID)
    CALL Step3 (@BatchID)
IF error_count > 1
    SET @ErrorNumber = -1 -- indicate special condition
END

-- Replace table-valued parameter with a LOOP cursor over a source table
CREATE PROCEDURE LoopItems()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE var_OrderID INT;
    DECLARE var_Item VARCHAR(20);
    DECLARE var_Quantity SMALLINT;
    DECLARE ItemCursor CURSOR
        FOR SELECT OrderID, Item, Quantity FROM SourceTable;
    DECLARE CONTINUE HANDLER
        FOR NOT FOUND SET done = TRUE;
    OPEN ItemCursor;
    CursorStart: LOOP
    FETCH NEXT FROM ItemCursor
        INTO var_OrderID, var_Item, var_Quantity;
    IF Done THEN LEAVE CursorStart;
    END IF;
        INSERT INTO OrderItems (OrderID, Item, Quantity)
        VALUES (var_OrderID, var_Item, var_Quantity);
    END LOOP;
    CLOSE ItemCursor;
END;

CALL LoopItems();
```

## Conversion notes

- Use `PROCEDURE` not `PROC`; omit the `AS` keyword; wrap parameters in parentheses; drop the `@` prefix from parameter names.
- Parameter direction: `OUTPUT` → `OUT`; use `INOUT` for bidirectional. `IN` is default in both.
- Security context: `EXECUTE AS 'user'` → `DEFINER = 'user'` + `SQL SECURITY DEFINER`; `CALLER` → `SQL SECURITY INVOKER`; `SELF` → `DEFINER = CURRENT_USER` + `SQL SECURITY DEFINER`. `OWNER` must be named explicitly.
- Not supported in Aurora MySQL: `WITH ENCRYPTION`, `WITH RECOMPILE`, table-valued parameters, `INSERT…EXEC`, `RETURN <int>`.
  - Table-valued params → use a source/temp table + cursor loop.
  - `INSERT…EXEC` → use tables, or pass CSV/XML/JSON strings and parse before insert.
  - `RETURN` value → use a standard `OUT` parameter.
- `LOAD DATA` is not allowed inside stored procedures (SQL Server allows `BULK INSERT`).

| Feature | SQL Server | Aurora MySQL | Workaround |
|---|---|---|---|
| CREATE syntax | `CREATE PROC\|PROCEDURE … AS <body>`, `@param` | `CREATE PROCEDURE (param…) <body>` | Use `PROCEDURE`, omit `AS`, parenthesize params, drop `@` |
| Security context | `EXECUTE AS {CALLER\|SELF\|OWNER\|'user'}` | `DEFINER=… SQL SECURITY {DEFINER\|INVOKER}` | Map as above |
| Encryption | `WITH ENCRYPTION` | Not supported | — |
| Parameter direction | `IN`, `OUT\|OUTPUT` | `IN`, `OUT`, `INOUT` | `OUT` for `OUTPUT`; `INOUT` bidirectional |
| Recompile | `WITH RECOMPILE` | Not supported | — |
| Table-valued params | declared table types | Not supported | source table + cursor loop |
| `INSERT…EXEC` | supported | Not supported | tables or CSV/XML/JSON parse |
| Additional | `BULK INSERT` | `LOAD DATA` not allowed in procedures | — |
| `RETURN` value | `RETURN <int>` | Not supported | use `OUT` parameter |
