# Flow Control

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.flowcontrol.html

**Conversion category:** Assisted (four-star feature compatibility, three-star automation)
**SCT automation:** Three-star automation level; SCT action code index: Flow Control

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Corrected the PostgreSQL keyword list (ITERATE/LEAVE/REPEAT are MySQL; ITERATE fails on 18.6), %s→% in RAISE, function→CREATE PROCEDURE, DO-block variables, WAITFOR TIME→pg_sleep_until (verified), GOTO rewrites.

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
- `CONTINUE [label] [WHEN cond]` — restart a LOOP/WHILE/FOR
- `EXIT [label] [WHEN cond]` — leave a loop or a labeled block
- `LOOP` — loop indefinitely
- `WHILE cond LOOP` / `FOR i IN a..b LOOP` / `FOR rec IN query LOOP` / `FOREACH x IN ARRAY arr LOOP`
- `RETURN` — terminate current scope
- `CASE … END CASE` (statement form)

> Correction: the playbook's original list (`ITERATE`, `LEAVE`, `REPEAT … UNTIL`) is MySQL syntax. PL/pgSQL rejects `ITERATE` (verified: syntax error on 18.6); there is no `REPEAT … UNTIL` — write `LOOP … EXIT WHEN cond; END LOOP`.

PostgreSQL variables need a PL/pgSQL body: a function, a procedure, or an anonymous `DO $$ … $$` block (a `DO` block works for one-off batch scripts but cannot take parameters or return rows). Equivalent of the SQL Server example (a procedure, because it returns nothing; `%` is the placeholder — `%s` would print a literal `s`):

```sql
CREATE OR REPLACE PROCEDURE p()
  LANGUAGE plpgsql
AS $procedure$
DECLARE
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
      RAISE NOTICE 'EXECUTING LogLargeOrder - % %', var_OrderID, var_NumItems;
    ELSE
      RAISE NOTICE 'EXECUTING LogSmallOrder - % %', var_OrderID, var_NumItems;
    END IF;
    END LOOP;
CLOSE OrderItemCursor;
END; $procedure$;
```

Simpler and preferred: `FOR r IN SELECT OrderID, SUM(Quantity) AS NumItems FROM OrderItems GROUP BY OrderID ORDER BY OrderID LOOP … END LOOP;` opens, fetches and closes the cursor implicitly.

## Summary

| Command | SQL Server | Aurora PostgreSQL |
|---|---|---|
| `BEGIN…END` | block boundaries | block boundaries |
| `RETURN` | exit scope (scripts + modules) | exit a function/procedure (`RETURN;` in a procedure; `RETURN <int>` status codes → an `INOUT`/`OUT` parameter) |
| `BREAK` | exit WHILE loop | `EXIT [label] [WHEN]` |
| `CONTINUE` | restart WHILE loop | `CONTINUE [label] [WHEN]` |
| `THROW` | raise errors | raise errors |
| `TRY…CATCH` | error handling | error handling (BEGIN..EXCEPTION) |
| `GOTO` | jump to label | Not supported — rewrite with `CASE` or nested procedures (`IF <condition> EXEC <proc>`) |
| `WAITFOR` | delay | `WAITFOR DELAY` → `pg_sleep(sec)` / `pg_sleep_for(interval)`; `WAITFOR TIME` → `pg_sleep_until(timestamptz)` |
| `IF… ELSE` | conditional | conditional |
| `WHILE` | loop while true | loop while true |

## Conversion notes
- **`GOTO` not supported** — refactor using `CASE`, nested stored procedures, or `IF <condition> EXEC <proc>`.
- `WAITFOR DELAY '00:00:05'` → `PERFORM pg_sleep(5)` or `pg_sleep_for('5 seconds')`; `WAITFOR TIME '22:00'` → `pg_sleep_until('22:00')` (verified on 18.6). A sleeping session holds its transaction and snapshot open; for scheduling, prefer `pg_cron`. `WAITFOR (RECEIVE …)` has no equivalent (see `service-broker.md`).
- `BREAK` → `EXIT`; `CONTINUE` → `CONTINUE` (not `ITERATE`, which is MySQL).
- `GOTO`: PL/pgSQL has no `GOTO`. `GOTO` to an error/cleanup label → `RAISE` + `EXCEPTION` handler; `GOTO` to the end → `RETURN` or `EXIT <block_label>` on a labeled block.
- Loop using `LOOP ... EXIT WHEN NOT FOUND` with `FOUND` instead of `@@FETCH_STATUS`.
- Variables and procedural flow must be inside a function, procedure or `DO` block, not a plain SQL batch.
- `PRINT` → `RAISE NOTICE` with `%` placeholders.
