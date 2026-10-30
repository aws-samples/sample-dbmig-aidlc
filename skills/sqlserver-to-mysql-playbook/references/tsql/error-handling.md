# Error handling for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.errorhandling.html

**Conversion category:** Assisted (Four star feature compatibility — different paradigm requires rewrite)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected 'no variables in SIGNAL' (SET items accept variables, SQLSTATE must be literal — verified), UNDO handlers rejected (verified), GET DIAGNOSTICS mapping (verified), RAISERROR severity, @@ERROR/XACT_ABORT patterns, rollback scope.

## SQL Server

Since SQL Server 2008, supports .NET-like error handling: `TRY/CATCH` blocks, `THROW`, `FORMATMESSAGE`, error-state functions, plus legacy `RAISERROR`.

### TRY/CATCH

```sql
BEGIN TRY
<Set of SQL Statements>
END TRY
BEGIN CATCH
<Set of SQL Error Handling Statements>
END CATCH
```

### THROW

```sql
THROW [<Error Number>, <Error Message>, <Error State>] [;]
```

```sql
-- rethrow on key violation
BEGIN TRY
    BEGIN TRANSACTION
        INSERT INTO ErrorTest(Col1) VALUES(1);
        INSERT INTO ErrorTest(Col1) VALUES(2);
        INSERT INTO ErrorTest(Col1) VALUES(1);
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    THROW; -- Throw with no parameters = RETHROW
END CATCH;

-- THROW with variables
BEGIN CATCH
DECLARE @CustomMessage VARCHAR(1000), @CustomError INT, @CustomState INT;
SET @CustomMessage = 'My Custom Text ' + ERROR_MESSAGE();
SET @CustomError = 54321;
SET @CustomState = 1;
THROW @CustomError, @CustomMessage, @CustomState;
END CATCH;
```

Note: per ANSI, a constraint violation does not roll back the whole transaction; the prior valid INSERTs (1 and 2) are committed.

### RAISERROR

```sql
RAISERROR (<Message ID>|<Message Text>, <Message Severity>, <Message State>
[WITH option [<Option List>]])

RAISERROR (N'This is a custom error message with severity 10 and state 1.', 10, 1)
```

Differences `THROW` vs `RAISERROR`: `RAISERROR` message IDs must exist in `sys.messages` (THROW's need not); `RAISERROR` supports printf formatting (THROW doesn't); `RAISERROR` uses its severity param (THROW is always severity 16).

### FORMATMESSAGE

```sql
FORMATMESSAGE (<Message Number> | <Message String>, <Parameter List>)
```

### Error-state functions

`ERROR_LINE`, `ERROR_MESSAGE`, `ERROR_NUMBER`, `ERROR_PROCEDURE`, `ERROR_SEVERITY`, `ERROR_STATE`, `@@ERROR` — used inside `CATCH`.

## MySQL

Aurora MySQL uses a different paradigm:
* `CONDITION` — equivalent of an `ERROR`.
* `HANDLER` — object that handles conditions and performs actions.
* `DIAGNOSTICS` — metadata about the condition.
* `SIGNAL`/`RESIGNAL` — similar to `THROW`/`RAISERROR`.

Errors identified by: a MySQL-specific numeric code, a 5-char ANSI/ODBC `SQLSTATE` value (general `HY000` if none), and a message string. `SQLSTATE` prefixes: `00`=success, `01`=warning (`SQLWARNING`), `02`=not found (`NOT FOUND`), other=`SQLEXCEPTION`.

### DECLARE … CONDITION

```sql
DECLARE <Condition Name> CONDITION
FOR <Condition Value>
-- <Condition Value> = <MySQL Error Code> | SQLSTATE [VALUE] <SQLState Value>

DECLARE TableDoesNotExist CONDITION FOR 1051;
DECLARE TableDoesNotExist CONDITION FOR SQLSTATE VALUE '42S02';
```

### DECLARE … HANDLER

```sql
DECLARE {CONTINUE | EXIT}          -- UNDO is listed in the grammar but is a syntax error (verified)
HANDLER FOR
<MySQL Error Code> |
SQLSTATE [VALUE] <SQLState Value> |
<Condition Name> |
SQLWARNING |
NOT FOUND |
SQLEXCEPTION
<Statement Block>

-- ignore warnings and continue
DECLARE CONTINUE HANDLER FOR SQLWARNING BEGIN END

-- EXIT on duplicate key, log to a table
DECLARE EXIT HANDLER
FOR SQLSTATE '23000'
BEGIN
    INSERT INTO MyErrorLogTable
        VALUES(NOW(), CURRENT_USER(), 'Error 23000')
END
```

### GET DIAGNOSTICS

```sql
GET [CURRENT | STACKED] DIAGNOSTICS
<@Parameter = NUMBER | ROW_COUNT>
| CONDITION <Condition Number> <@Parameter = CLASS_ORIGIN | SUBCLASS_ORIGIN |
RETURNED_SQLSTATE | MESSAGE_TEXT | MYSQL_ERRNO | ...>

GET DIAGNOSTICS CONDITION 1 @p1 = RETURNED_SQLSTATE, @p2 = MESSAGE_TEXT
```

Also supports `SHOW WARNINGS` / `SHOW ERRORS`.

### SIGNAL / RESIGNAL

```sql
SIGNAL | RESIGNAL <SQLSTATE [VALUE] sqlstate_value | <Condition Name>
[SET <Condition Information Item Name> = <Value> [,...n]]

SIGNAL SQLSTATE '55555'
RESIGNAL SET MYSQL_ERRNO = 5
```

`RESIGNAL` passes on condition info during handler execution, optionally changing some/all of it. *(corrected)* The **`SQLSTATE` value must be a literal** (a variable is a syntax error, verified), but the `SET` items **can** use variables: `SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg, MYSQL_ERRNO = 50001` works (verified on 3.13 and 8.4.8), so `THROW 50001, @msg, 1` converts directly.

## Conversion notes

- Map `TRY/CATCH` → nested `BEGIN…END` blocks with per-scope `DECLARE … HANDLER`. Handlers must be declared **first** (before the statements), unlike CATCH which follows.
- Map `THROW`/`RAISERROR` → `SIGNAL`/`RESIGNAL`. `THROW <num>, <msg variable>, <state>` → `SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg, MYSQL_ERRNO = <num>` (variables allowed in `SET`, verified). `FORMATMESSAGE` → build the text with `CONCAT()` first. `THROW;` (rethrow) → `RESIGNAL;` inside the handler.
- `ERROR_NUMBER()`, `ERROR_MESSAGE()`, `ERROR_STATE()` → `GET DIAGNOSTICS CONDITION 1 v_no = MYSQL_ERRNO, v_msg = MESSAGE_TEXT, v_state = RETURNED_SQLSTATE` inside the handler (verified: duplicate key gave 23000 / 1062 / *Duplicate entry '1' for key 'employees.PRIMARY'*). `ERROR_LINE()`/`ERROR_PROCEDURE()` have no equivalent.
- `RAISERROR(…, 10, …)` (informational, severity ≤ 10) → `SIGNAL SQLSTATE '01000'` (a warning that does not stop execution).
- `@@ERROR` after each statement → a `CONTINUE HANDLER` that sets a flag, or `GET DIAGNOSTICS @n = NUMBER`. `XACT_ABORT ON` → an `EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END` at the start of the procedure.
- **Rollback scope:** an error in MySQL rolls back only the failing statement (like SQL Server without `XACT_ABORT`); the transaction stays open, so the handler must `ROLLBACK` explicitly. Error code 1213 (deadlock) rolls back the whole transaction.
- Handler placement trap: a `CONTINUE HANDLER FOR NOT FOUND` declared for a cursor also catches a `SELECT … INTO` that finds no rows (see `cursors.md`).
- Map error-state functions → `GET DIAGNOSTICS`.
- Consider switching from proprietary error codes to standard `SQLSTATE` values.
- Handler scope/choice: SQL Server has one CATCH per statement (deterministic, next block in order). Aurora MySQL allows multiple handlers; precedence = MySQL error code > `SQLSTATE` > general (`SQLWARNING`/`SQLEXCEPTION`/`NOT FOUND`), and `SQLEXCEPTION` > `SQLWARNING`. Equal-precedence handlers → non-deterministic choice.

| SQL Server feature | Aurora MySQL | Comments |
|---|---|---|
| `TRY/CATCH` blocks | Nested `BEGIN…END` with per-scope handlers | Handlers declared first |
| `THROW`, `RAISERROR` | `SIGNAL`, `RESIGNAL` | |
| `THROW` with variables | `SIGNAL … SET MESSAGE_TEXT = var` | `SQLSTATE` itself must be a literal |
| `FORMATMESSAGE` | N/A | |
| Error-state functions | `GET DIAGNOSTICS` | |
| `sys.messages` codes | MySQL codes + ANSI/ODBC `SQLSTATE` | Prefer `SQLSTATE` |
| Deterministic handler order | May be non-deterministic | Same precedence/scope |
