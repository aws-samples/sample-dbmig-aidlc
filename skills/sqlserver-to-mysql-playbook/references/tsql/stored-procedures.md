# Stored procedures for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.storedprocedures.html

**Conversion category:** Assisted (Three star feature compatibility)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Fixed the broken RETURN-value example (still T-SQL syntax); corrected the binary-logging note (affects creating functions/triggers); JSON_TABLE for TVPs (toolkit convention); verified no defaults, no named calls, no overloading, 64-char names, DEFINER behavior.

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

Aurora MySQL stored procedures offer similar functionality, supporting security run context and IN/OUT/INOUT parameters. Stored procedures, triggers, and UDFs are collectively *stored routines*. *(corrected)* With binary logging enabled, **creating stored functions and triggers** that are not `DETERMINISTIC`/`NO SQL`/`READS SQL DATA` requires `log_bin_trust_function_creators` = 1 in the DB cluster parameter group (the Aurora master user has no `SUPER`; the parameter is 0 and binary logging is off by default — verified). Procedures are not affected. Functions and triggers cannot commit or run DDL (error 1422, verified). Routines may contain control flow, DML, DDL, and transaction management (`START TRANSACTION`, `COMMIT`, `ROLLBACK`).

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
-- (the original example kept T-SQL syntax: @-prefixed parameters outside the parentheses, no semicolons)
CREATE PROCEDURE ProcessImportBatch(IN BatchID INT, OUT ErrorNumber INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1 ErrorNumber = MYSQL_ERRNO;
    END;
    SET ErrorNumber = 0;
    CALL Step1(BatchID);
    CALL Step2(BatchID);
    CALL Step3(BatchID);
END;
-- CALL ProcessImportBatch(42, @err); SELECT @err;
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
  - Table-valued params → a **JSON parameter** expanded with `JSON_TABLE(p_items, '$[*]' COLUMNS (…))` inside the procedure (set-based; MySQL 8 — the toolkit's preferred mapping, `engines/sqlserver-to-mysql/checks/non-portable-constructs.md`), or a temporary table filled by the caller.
  - `INSERT…EXEC` → use tables, or pass CSV/XML/JSON strings and parse before insert.
  - `RETURN` value → use a standard `OUT` parameter.
- `LOAD DATA` is not allowed inside stored procedures (SQL Server allows `BULK INSERT`); `LOAD DATA FROM S3` must also run outside routines.

Verified on Aurora MySQL 3.13 and 8.4.8:
- **No parameter defaults** (`IN a INT DEFAULT 1` is a syntax error) — every caller passes all arguments; T-SQL optional parameters → pass `NULL` and `COALESCE` inside.
- **No named-parameter calls** (`EXEC p @x = 1`) — `CALL p(1)` positionally; reorder call sites.
- **No overloading** (error 1304) and routine names ≤ **64 characters** (error 1059).
- Result sets: a procedure returns each `SELECT` as a result set to the caller, like SQL Server; `INSERT … EXEC p` → have `p` write into a temporary table that the caller reads (temporary tables persist for the session).
- `OUT`/`INOUT` arguments must be user or local variables: `CALL p(42, @err); SELECT @err;`.
- `SET NOCOUNT ON` → remove. `@@ROWCOUNT` → `ROW_COUNT()` immediately after the DML.
- `EXECUTE AS OWNER` → `SQL SECURITY DEFINER` with a `DEFINER` account that exists; the master user can set any `DEFINER` (verified), and on 8.4 that needs `SET_ANY_DEFINER`.
- Recursion is off (`max_sp_recursion_depth` = 0); raise it per session for recursive procedures.

| Feature | SQL Server | Aurora MySQL | Workaround |
|---|---|---|---|
| CREATE syntax | `CREATE PROC\|PROCEDURE … AS <body>`, `@param` | `CREATE PROCEDURE (param…) <body>` | Use `PROCEDURE`, omit `AS`, parenthesize params, drop `@` |
| Security context | `EXECUTE AS {CALLER\|SELF\|OWNER\|'user'}` | `DEFINER=… SQL SECURITY {DEFINER\|INVOKER}` | Map as above |
| Encryption | `WITH ENCRYPTION` | Not supported | — |
| Parameter direction | `IN`, `OUT\|OUTPUT` | `IN`, `OUT`, `INOUT` | `OUT` for `OUTPUT`; `INOUT` bidirectional |
| Recompile | `WITH RECOMPILE` | Not supported | — |
| Table-valued params | declared table types | Not supported | JSON parameter + `JSON_TABLE`, or a temporary table |
| `INSERT…EXEC` | supported | Not supported | procedure writes to a temporary table |
| Parameter defaults / named calls | supported | Not supported | pass every argument positionally |
| Additional | `BULK INSERT` | `LOAD DATA` not allowed in procedures | — |
| `RETURN` value | `RETURN <int>` | Not supported | use `OUT` parameter |
