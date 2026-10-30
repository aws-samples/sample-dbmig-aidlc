# Flow control for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.flowcontrol.html

**Conversion category:** Automatic (Four star feature compatibility — syntax differences, similar functionality)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected BREAK/CONTINUE (LEAVE/ITERATE with labels — verified) and RETURN in procedures (LEAVE proc label — verified); rewrote the broken GOTO example in MySQL syntax; SLEEP fractions, user variables in scripts, ELSEIF, PRINT.

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

-- GOTO / conditional step rewritten with IF … THEN … END IF
-- (the original example was still T-SQL: @variables, IF … BEGIN … END, missing semicolons)
CREATE PROCEDURE ProcessOrderItems
(Var_OrderID INT, Var_Item VARCHAR(20), Var_Quantity INT, UpdateInventory TINYINT)
BEGIN
    INSERT INTO OrderItems (OrderID, Item, Quantity)
    VALUES (Var_OrderID, Var_Item, Var_Quantity);
    IF UpdateInventory = 1 THEN
        UPDATE Inventory
        SET Stock = Stock - Var_Quantity
        WHERE Item = Var_Item;
    END IF;
END;
```

## Conversion notes

- `BEGIN…END`, `IF…ELSE`, `WHILE` compatible in functionality but syntax differs.
- `IF`: SQL Server `IF <cond> <stmt> ELSE <stmt>` → Aurora `IF <cond> THEN <stmt> ELSE <stmt> END IF` (add `THEN`/`END IF`).
- `WHILE`: SQL Server `WHILE <cond> BEGIN…END` → Aurora `WHILE <cond> DO… END WHILE` (no `BEGIN…END` needed).
- `RETURN`: Aurora valid only in stored functions. In a procedure, label the body and use `LEAVE proc_label;` for an early exit (verified: `proc: BEGIN … LEAVE proc; … END`). `RETURN <int>` status codes → an `OUT` parameter.
- *(corrected)* `BREAK` → **`LEAVE <loop_label>`** and `CONTINUE` → **`ITERATE <loop_label>`**; label the loop (`l: WHILE … DO … END WHILE l;`). Verified on 3.13 and 8.4.8. No flag variable needed.
- `THROW`/`TRY-CATCH`: handled via `HANDLER` objects (see Error Handling).
- `GOTO`: not supported → rewrite with `CASE`, nested blocks, or `IF <cond> CALL <proc>`.
- `WAITFOR DELAY` → `DO SLEEP(n)` (fractional seconds work, verified `SLEEP(0.2)`). `WAITFOR TIME` → `DO SLEEP(TIMESTAMPDIFF(SECOND, NOW(), '2026-10-30 22:00:00'))`, or better a one-time `CREATE EVENT … AT …`. A sleeping session keeps its transaction open.
- Local variables (`DECLARE`) exist only in stored routines; ad-hoc scripts can use **user variables** (`SET @x = …`), which are session-global and untyped. T-SQL `DECLARE @x INT` in a batch → `SET @x = …`, or wrap the batch in a temporary procedure.
- `IF EXISTS (SELECT …)` works inside routines; `IF … ELSE IF …` → `IF … ELSEIF … END IF`.
- `PRINT` → `SELECT` (result set) or `SIGNAL SQLSTATE '01000'` (warning).

| Feature | SQL Server | Aurora MySQL | Workaround |
|---|---|---|---|
| `BEGIN…END` | block | block | Compatible |
| `RETURN` | any module, scripts; can return value | functions only | `LEAVE proc_label` in procedures; OUT params for values |
| `BREAK` / `CONTINUE` | exit / restart `WHILE` | `LEAVE label` / `ITERATE label` | label the loop (verified) |
| `THROW` | raise errors | `HANDLER` objects | see Error Handling |
| `TRY-CATCH` | error handling | `HANDLER` objects | see Error Handling |
| `GOTO` | jump to label | Not supported | `CASE`/nested procs/`IF…CALL` |
| `WAITFOR` | delay | `DO SLEEP(n)` | fractional seconds; `CREATE EVENT` for a wall-clock time |
| `IF…ELSE` | `IF <c> <s> ELSE <s>` | `IF <c> THEN <s> ELSE <s> END IF` | add `THEN`/`END IF` |
| `WHILE` | `WHILE <c> BEGIN…END` | `WHILE <c> DO… END WHILE` | rewrite keywords |
