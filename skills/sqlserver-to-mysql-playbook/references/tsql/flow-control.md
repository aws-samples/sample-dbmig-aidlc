# Flow control for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.flowcontrol.html

**Conversion category:** Automatic (Four star feature compatibility — syntax differences, similar functionality)
**SCT automation:** Four star automation level

## SQL Server

Flow-control keywords:
* `BEGIN… END` — block boundaries
* `RETURN` — exit module, optionally return INT
* `BREAK` — exit `WHILE` loop
* `THROW` — raise errors
* `CONTINUE` — restart `WHILE` loop
* `TRY… CATCH` — error handling
* `GOTO label` — jump to label
* `WAITFOR` — delay
* `IF… ELSE` — conditional
* `WHILE <condition>` — loop while true (often used with cursors via `@@FETCH_STATUS`)

### Examples

```sql
-- WAITFOR: one-minute delay between purge batches
SET ROWCOUNT 1000;
WHILE @@ROWCOUNT > 0;
BEGIN;
    DELETE FROM OrderItems
    WHERE OrderDate < '19900101';
    WAITFOR DELAY '00:01:00';
END;

-- GOTO: skip a section based on parameter
CREATE PROCEDURE ProcessOrderItems
@OrderID INT, @Item VARCHAR(20), @Quantity INT, @UpdateInventory BIT
AS
BEGIN
        INSERT INTO OrderItems (OrderID, Item, Quantity)
        SELECT @OrderID, @item, @Quantity
    IF @UpdateInventory = 0
        GOTO Finish
    UPDATE Inventory
    SET Stock = Stock - @Quantity
    WHERE Item = @Item
finish:
END
```

## MySQL

Flow-control constructs:
* `BEGIN… END` — block boundaries
* `CASE` — run commands based on a predicate
* `IF… ELSE` — conditional
* `ITERATE` — restart a `LOOP`/`REPEAT`/`WHILE`
* `LEAVE` — exit a module/loop
* `LOOP` — loop indefinitely
* `REPEAT… UNTIL` — loop until predicate true
* `RETURN` — terminate current scope (functions only)
* `WHILE` — loop while true
* `SLEEP` — pause N seconds

### Examples

```sql
-- WAITFOR rewritten with SLEEP
CREATE PROCEDURE P()
BEGIN
    DECLARE RR INT;
    SET RR = (SELECT COUNT(*) FROM OrderItems WHERE OrderDate < '19900101');
    WHILE RR > 0 DO
        DELETE FROM OrderItems WHERE OrderDate < '19900101';
        DO SLEEP (60);
        SET RR = (SELECT COUNT(*) FROM OrderItems WHERE OrderDate < '19900101');
    END WHILE;
END;

-- GOTO rewritten with nested blocks
CREATE PROCEDURE ProcessOrderItems
(Var_OrderID INT, Var_Item VARCHAR(20), Var_Quantity INT, UpdateInventory BIT)
BEGIN
        INSERT INTO OrderItems (OrderID, Item, Quantity)
        VALUES(Var_OrderID, Var_Item, Var_Quantity)
    IF @UpdateInventory = 1
    BEGIN
        UPDATE Inventory
        SET Stock = Stock - @Quantity
        WHERE Item = @Item
    END
END
```

## Conversion notes

- `BEGIN…END`, `IF…ELSE`, `WHILE` compatible in functionality but syntax differs.
- `IF`: SQL Server `IF <cond> <stmt> ELSE <stmt>` → Aurora `IF <cond> THEN <stmt> ELSE <stmt> END IF` (add `THEN`/`END IF`).
- `WHILE`: SQL Server `WHILE <cond> BEGIN…END` → Aurora `WHILE <cond> DO… END WHILE` (no `BEGIN…END` needed).
- `RETURN`: Aurora valid only in stored/UDF functions, not procedures/triggers/events; cannot return a value via `LEAVE` (use OUT params); cannot `RETURN` in non-routine scripts.
- `BREAK`: not supported → set a control flag making the `WHILE` condition false and `ITERATE` to loop top.
- `THROW`/`TRY-CATCH`: handled via `HANDLER` objects (see Error Handling).
- `GOTO`: not supported → rewrite with `CASE`, nested blocks, or `IF <cond> CALL <proc>`.
- `WAITFOR`: not supported → use `SLEEP` (seconds only). `WAITFOR TIME` → compute seconds difference and `SLEEP`, or use `CREATE EVENT`.
- Aurora MySQL variables usable only in stored routines (not ad-hoc batch scripts).

| Feature | SQL Server | Aurora MySQL | Workaround |
|---|---|---|---|
| `BEGIN…END` | block | block | Compatible |
| `RETURN` | any module, scripts; can return value | functions only | Use `LEAVE`; OUT params for values |
| `BREAK` | exit `WHILE` | Not supported | control flag + `ITERATE` |
| `THROW` | raise errors | `HANDLER` objects | see Error Handling |
| `TRY-CATCH` | error handling | `HANDLER` objects | see Error Handling |
| `GOTO` | jump to label | Not supported | `CASE`/nested procs/`IF…CALL` |
| `WAITFOR` | delay | Not supported | `SLEEP` (sec); `CREATE EVENT` |
| `IF…ELSE` | `IF <c> <s> ELSE <s>` | `IF <c> THEN <s> ELSE <s> END IF` | add `THEN`/`END IF` |
| `WHILE` | `WHILE <c> BEGIN…END` | `WHILE <c> DO… END WHILE` | rewrite keywords |
