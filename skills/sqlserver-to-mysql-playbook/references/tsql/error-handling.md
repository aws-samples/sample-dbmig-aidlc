# Error handling for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.errorhandling.html

**Conversion category:** Assisted (Four star feature compatibility — different paradigm requires rewrite)
**SCT automation:** Four star automation level

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
DECLARE {CONTINUE | EXIT | UNDO}
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

`RESIGNAL` passes on condition info during handler execution, optionally changing some/all of it. Cannot use variables in `SIGNAL`.

## Conversion notes

- Map `TRY/CATCH` → nested `BEGIN…END` blocks with per-scope `DECLARE … HANDLER`. Handlers must be declared **first** (before the statements), unlike CATCH which follows.
- Map `THROW`/`RAISERROR` → `SIGNAL`/`RESIGNAL`. `THROW` with variables is not supported. `FORMATMESSAGE` has no equivalent.
- Map error-state functions → `GET DIAGNOSTICS`.
- Consider switching from proprietary error codes to standard `SQLSTATE` values.
- Handler scope/choice: SQL Server has one CATCH per statement (deterministic, next block in order). Aurora MySQL allows multiple handlers; precedence = MySQL error code > `SQLSTATE` > general (`SQLWARNING`/`SQLEXCEPTION`/`NOT FOUND`), and `SQLEXCEPTION` > `SQLWARNING`. Equal-precedence handlers → non-deterministic choice.

| SQL Server feature | Aurora MySQL | Comments |
|---|---|---|
| `TRY/CATCH` blocks | Nested `BEGIN…END` with per-scope handlers | Handlers declared first |
| `THROW`, `RAISERROR` | `SIGNAL`, `RESIGNAL` | |
| `THROW` with variables | Not supported | |
| `FORMATMESSAGE` | N/A | |
| Error-state functions | `GET DIAGNOSTICS` | |
| `sys.messages` codes | MySQL codes + ANSI/ODBC `SQLSTATE` | Prefer `SQLSTATE` |
| Deterministic handler order | May be non-deterministic | Same precedence/scope |
