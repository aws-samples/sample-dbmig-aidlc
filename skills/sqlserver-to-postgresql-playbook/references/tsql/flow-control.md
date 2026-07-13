# Flow Control

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.flowcontrol.html

**Conversion category:** Assisted (four-star feature compatibility, three-star automation)
**SCT automation:** Three-star automation level; SCT action code index: Flow Control

## SQL Server

Flow control keywords:
- `BEGIN… END` — block boundaries
- `RETURN` — exit a code module (`RETURN <value>` returns an INT)
- `BREAK` — exit a WHILE loop
- `THROW` — raise errors
- `CONTINUE` — restart a WHILE loop
- `TRY… CATCH` — error handling
- `GOTO label` — jump to a label
- `WAITFOR` — delay
- `IF… ELSE` — conditional
- `WHILE <condition>` — loop while TRUE

WHILE loops commonly use cursors with `@@FETCH_STATUS` to determine exit.

Example — cursor loop with IF/ELSE:

```sql
DECLARE OrderItemCursor CURSOR FAST_FORWARD
FOR
SELECT OrderID, SUM(Quantity) AS NumItems
FROM OrderItems
GROUP BY OrderID
ORDER BY OrderID;

DECLARE @OrderID INT, @NumItems INT;
OPEN OrderItemCursor;
FETCH NEXT FROM OrderItemCursor INTO @OrderID, @NumItems

WHILE @@Fetch_Status = 0
BEGIN;
  IF @NumItems > 100
    PRINT 'EXECUTING LogLargeOrder - ' + CAST(@OrderID AS VARCHAR(5)) + ' ' + CAST(@NumItems AS VARCHAR(5));
  ELSE
    PRINT 'EXECUTING LogSmallOrder - ' + CAST(@OrderID AS VARCHAR(5)) + ' ' + CAST(@NumItems AS VARCHAR(5));
  FETCH NEXT FROM OrderItemCursor INTO @OrderID, @NumItems;
END;
CLOSE OrderItemCursor;
DEALLOCATE OrderItemCursor;
```

## PostgreSQL

Flow control constructs:
- `BEGIN… END` — block boundaries
- `CASE` — run commands based on a predicate
- `IF… ELSE` — conditional
- `ITERATE` — restart a LOOP/WHILE
- `LEAVE` — exit a code module
- `LOOP` — loop indefinitely
- `REPEAT… UNTIL` — loop until predicate true
- `RETURN` — terminate current scope
- `WHILE` — loop while TRUE

PostgreSQL variables can only be used in stored routines (procedures/functions), not batch scripts. Equivalent of the SQL Server example:

```sql
CREATE OR REPLACE FUNCTION P()
  RETURNS numeric
  LANGUAGE plpgsql
AS $function$
DECLARE
  done int default false;
  var_OrderID int;
  var_NumItems int;
  OrderItemCursor CURSOR FOR SELECT OrderID, SUM(Quantity) AS NumItems
  FROM OrderItems GROUP BY OrderID ORDER BY OrderID;
  BEGIN
    OPEN OrderItemCursor;
    LOOP
      fetch from OrderItemCursor INTO var_OrderID, var_NumItems;
    EXIT WHEN NOT FOUND;
    IF var_NumItems > 100 THEN
      RAISE NOTICE 'EXECUTING LogLargeOrder - %s',var_OrderID;
      RAISE NOTICE 'Num Items: %s', var_NumItems;
    ELSE
      RAISE NOTICE 'EXECUTING LogSmallOrder - %s',var_OrderID;
      RAISE NOTICE 'Num Items: %s', var_NumItems;
    END IF;
    END LOOP;
done = TRUE;
CLOSE OrderItemCursor;
END; $function$
```

## Summary

| Command | SQL Server | Aurora PostgreSQL |
|---|---|---|
| `BEGIN…END` | block boundaries | block boundaries |
| `RETURN` | exit scope (scripts + modules) | exit a stored function |
| `BREAK` | exit WHILE loop | `EXIT WHEN` |
| `THROW` | raise errors | raise errors |
| `TRY…CATCH` | error handling | error handling (BEGIN..EXCEPTION) |
| `GOTO` | jump to label | Not supported — rewrite with `CASE` or nested procedures (`IF <condition> EXEC <proc>`) |
| `WAITFOR` | delay | `pg_sleep` (WAITFOR TIME not supported) |
| `IF… ELSE` | conditional | conditional |
| `WHILE` | loop while true | loop while true |

## Conversion notes
- **`GOTO` not supported** — refactor using `CASE`, nested stored procedures, or `IF <condition> EXEC <proc>`.
- **`WAITFOR TIME` not supported**; `WAITFOR DELAY` → `pg_sleep(seconds)`.
- `BREAK` → `EXIT WHEN`; `CONTINUE` → `ITERATE`/`CONTINUE`.
- Loop using `LOOP ... EXIT WHEN NOT FOUND` with `FOUND` instead of `@@FETCH_STATUS`.
- Variables and procedural flow must be inside a function/procedure, not a standalone batch.
