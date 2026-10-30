# Error Handling

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.errorhandling.html

**Conversion category:** Manual (two-star feature compatibility — different paradigm requires rewrite; three-star automation)
**SCT automation:** Three-star automation level; N/A action code

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): TRY…CATCH patterns with GET STACKED DIAGNOSTICS, THROW→RAISE…USING ERRCODE and safe custom SQLSTATE choice, @@ERROR mapping, and the verified rollback-scope difference (EXCEPTION blocks roll back the whole block, not just the failing statement) added.

## SQL Server

From SQL Server 2008, .NET-like error handling: `TRY…CATCH`, `THROW`, `FORMATMESSAGE`, and error-state functions. Pre-2008 used `RAISERROR`.

**TRY…CATCH** — errors in the TRY block transfer control to the nearest CATCH block:

```sql
BEGIN TRY
<Set of SQL Statements>
END TRY
BEGIN CATCH
<Set of SQL Error Handling Statements>
END CATCH
```

**THROW** — raises an exception (severity always 16); accepts literals or variables:

```sql
THROW [Error Number>, <Error Message>, < Error State>] [;]
```

Example (THROW with no parameters = RETHROW):

```sql
BEGIN TRY
  BEGIN TRANSACTION
    INSERT INTO ErrorTest(Col1) VALUES(1);
    INSERT INTO ErrorTest(Col1) VALUES(2);
    INSERT INTO ErrorTest(Col1) VALUES(1);
  COMMIT TRANSACTION;
END TRY
BEGIN CATCH
  THROW; -- RETHROW
END CATCH;
```
Note: per ANSI, the constraint violation does not roll back the whole transaction — rows 1 and 2 are inserted.

THROW with variables:

```sql
BEGIN CATCH
DECLARE @CustomMessage VARCHAR(1000), @CustomError INT, @CustomState INT;
SET @CustomMessage = 'My Custom Text ' + ERROR_MESSAGE();
SET @CustomError = 54321;
SET @CustomState = 1;
THROW @CustomError, @CustomMessage, @CustomState;
END CATCH;
```

**RAISERROR** — differs from THROW: message IDs must exist in `sys.messages` (THROW's needn't); supports `printf` formatting; uses a severity parameter.

```sql
RAISERROR (<Message ID>|<Message Text>, <Message Severity>, <Message State> [WITH option ...])
RAISERROR (N'This is a custom error message with severity 10 and state 1.', 10, 1)
```

**FORMATMESSAGE** — builds a message string from `sys.messages` or a text string with parameter replacement.

**Error-state functions**: `ERROR_LINE`, `ERROR_MESSAGE`, `ERROR_NUMBER`, `ERROR_PROCEDURE`, `ERROR_SEVERITY`, `ERROR_STATE`, `@@ERROR`.

## PostgreSQL

No native replacement, but comparable options. Trap errors with `BEGIN ... EXCEPTION ... END`. Any error in a PL/pgSQL block aborts the block and surrounding transaction unless trapped.

Syntax:

```sql
[ <<label>> ]
[ DECLARE declarations ]
BEGIN
  statements
EXCEPTION
  WHEN condition [ OR condition ... ] THEN
    handler_statements
  [ WHEN condition [ OR condition ... ] THEN
    handler_statements ... ]
END;
```

`condition` references the error name or SQLSTATE code, e.g. `WHEN interval_field_overflow THEN…` or `WHEN SQLSTATE '22015' THEN…`.

**RAISE** to throw errors/messages, with severity levels:

| Severity | Usage |
|---|---|
| DEBUG1..DEBUG5 | detailed developer info |
| INFO | info implicitly requested by user |
| NOTICE | helpful info to users |
| WARNING | likely problems |
| ERROR | aborts current command |
| LOG | admin info (e.g., checkpoints) |
| FATAL | aborts current session |
| PANIC | aborts all sessions |

Examples:

```sql
SET CLIENT_MIN_MESSAGES = 'debug';
DO $$
BEGIN
RAISE DEBUG USING MESSAGE := 'hello world';
END $$;
-- DEBUG: hello world
```

`client_min_messages` controls messages sent to client (default NOTICE); `log_min_messages` controls server log (default WARNING).

Handle division-by-zero:

```sql
BEGIN
  SELECT 5/0;
EXCEPTION
  WHEN division_by_zero THEN
    RAISE NOTICE 'caught division_by_zero';
  return 0;
END;
```

## Summary

| SQL Server feature | Aurora PostgreSQL equivalent |
|---|---|
| `TRY…CATCH` blocks | Inner `BEGIN ... EXCEPTION WHEN ... THEN END` |
| `THROW` and `RAISERROR` | `RAISE` |
| `FORMATMESSAGE` | `RAISE [level] 'format'` or `ASSERT` |
| Error state functions | `GET STACKED DIAGNOSTICS` |
| Proprietary error messages in `sys.messages` | `RAISE` |
| `@@ERROR` | No equivalent — wrap the statement in `BEGIN … EXCEPTION` and read `SQLSTATE`, or use `GET DIAGNOSTICS … ROW_COUNT` / `FOUND` for row checks |

## PostgreSQL 18 conversion patterns (verified on Aurora PostgreSQL 18.6)

```sql
-- TRY…CATCH + ERROR_MESSAGE()/ERROR_NUMBER()/ERROR_PROCEDURE()/ERROR_LINE()
DO $$
DECLARE v_msg text; v_state text; v_ctx text; v_detail text;
BEGIN
  PERFORM 1/0;
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_msg    = MESSAGE_TEXT,
                          v_state  = RETURNED_SQLSTATE,
                          v_detail = PG_EXCEPTION_DETAIL,
                          v_ctx    = PG_EXCEPTION_CONTEXT;   -- routine name + line (ERROR_PROCEDURE/ERROR_LINE)
  RAISE NOTICE '% %', v_state, v_msg;
END $$;

-- THROW 50001, 'Order 42 invalid', 1;
RAISE EXCEPTION 'Order % invalid', 42 USING ERRCODE = 'P0001', DETAIL = '...', HINT = '...';

-- THROW;   (rethrow inside CATCH)
EXCEPTION WHEN division_by_zero THEN RAISE;   -- bare RAISE re-raises the original SQLSTATE
```

- **Custom error numbers.** SQL Server's integer error numbers become 5-character SQLSTATEs. Use `P0001` (`raise_exception`) or a class that PostgreSQL never uses (for example `U0001`…`U9999`, verified). Do **not** map `50001` to `'50001'` or `54321` to `'54321'`: those land in real classes (`54` = program_limit_exceeded) and get caught by the wrong `WHEN` handlers. Keep the original number in `DETAIL` or `MESSAGE` if callers parse it.
- **`RAISERROR` severity.** Severity ≤ 10 is informational → `RAISE NOTICE`/`WARNING`; severity 11–19 → `RAISE EXCEPTION`; `WITH NOWAIT` → `RAISE NOTICE` (notices are sent immediately). `WITH LOG` → `RAISE LOG`.
- **`ASSERT`** raises SQLSTATE `P0004` (`assert_failure`) and can be disabled with `plpgsql.check_asserts = off`, so never use it for business rules.
- **Rollback scope differs (verified).** SQL Server rolls back only the failing *statement*; the example above keeps rows 1 and 2. In PL/pgSQL an `EXCEPTION` block rolls back **everything done since the block's `BEGIN`**: `INSERT 1; BEGIN INSERT 2; INSERT 1(dup); EXCEPTION … END` keeps only row 1. To keep SQL Server semantics, put each statement that may fail in its own `BEGIN … EXCEPTION … END` sub-block. Each sub-block is a subtransaction, so avoid them inside tight loops (subtransaction overhead and SLRU pressure).
- **`XACT_ABORT`.** Outside an exception block an error aborts the whole transaction; this matches `SET XACT_ABORT ON`. There is no `XACT_STATE()`; inside the handler the subtransaction has already been rolled back.
- **`COMMIT`/`ROLLBACK` inside a block with an `EXCEPTION` clause raises an error** (`cannot commit while a subtransaction is active`). If that block also has `WHEN OTHERS`, the handler catches the error and the COMMIT is silently lost. Move transaction control outside exception blocks (see `transactions.md`).

## Conversion notes
- Rewrite `TRY…CATCH` as a `BEGIN ... EXCEPTION` block; PL/pgSQL exception handling implicitly rolls back to the block start (a sub-transaction).
- `THROW`/`RAISERROR` → `RAISE` with severity level and optional `ERRCODE`/`MESSAGE`.
- Access error context with `GET STACKED DIAGNOSTICS` and predefined variables `SQLSTATE`/`SQLERRM`, replacing `ERROR_*` functions.
- Use condition names (e.g., `division_by_zero`) or SQLSTATE codes in `WHEN` clauses.
- Note transaction-rollback behavior differs: in PostgreSQL an unhandled error aborts the whole transaction.
