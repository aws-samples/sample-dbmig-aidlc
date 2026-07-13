# Transactions

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.transactions.html

**Conversion category:** Assisted (three-star feature compatibility, three-star automation)
**SCT automation:** Three-star automation level; SCT action code index: Transaction Isolation

## SQL Server

A transaction is an all-or-nothing unit of work complying with ACID (Atomic, Consistent, Isolation, Durable). By default SQL Server uses auto-commit / implicit transactions = ON; every statement is its own transaction unless one is explicitly defined.

Transaction boundary syntax:

```sql
BEGIN TRAN | TRANSACTION [<transaction name>]
COMMIT WORK | [ TRAN | TRANSACTION [<transaction name>]]
ROLLBACK WORK | [ TRAN | TRANSACTION [<transaction name>]]
```

ANSI isolation levels and the phenomena they prevent:

| Isolation level | Dirty reads | Non-repeatable reads | Phantom reads |
|---|---|---|---|
| Read uncommitted | Allowed | Allowed | Allowed |
| Read committed | Disallowed | Allowed | Allowed |
| Repeatable read | Disallowed | Disallowed | Allowed |
| Serializable | Disallowed | Disallowed | Disallowed |

Two isolation implementations: **Pessimistic (locking)** — single data copy, lock waits; **Optimistic (MVCC)** — per-transaction row versions, no waits but possible commit conflicts. SQL Server implements both and adds read-committed snapshot and snapshot isolation levels.

```sql
SET TRANSACTION ISOLATION LEVEL { READ UNCOMMITTED | READ COMMITTED | REPEATABLE READ | SNAPSHOT | SERIALIZABLE }
```

Example:

```sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
BEGIN TRANSACTION;
INSERT INTO Table1 VALUES (1, 'A');
UPDATE Table2 SET Column1 = 'Done' WHERE KeyColumn = 1;
COMMIT TRANSACTION;
```

## PostgreSQL

Same ANSI/ISO SQL92 isolation levels, with differences:

| Isolation level | Dirty reads | Non-repeatable reads | Phantom reads |
|---|---|---|---|
| Read uncommitted | Permitted but not implemented | Permitted | Permitted |
| Read committed | Not permitted | Permitted | Permitted |
| Repeatable read | Not permitted | Not permitted | Permitted but not implemented |
| Serializable | Not permitted | Not permitted | Not permitted |

PostgreSQL practically supports three levels — Read-Uncommitted behaves as Read-Committed. Repeatable-read is implemented so phantom reads don't occur (similar to Serializable); the difference is Serializable guarantees concurrent transactions produce exactly the same result as serial execution. From PostgreSQL 12 you can add `AND CHAIN` to `COMMIT`/`ROLLBACK` to immediately start another transaction with the same parameters.

**MVCC**: each transaction sees a consistent snapshot of data as of its start time, ignoring uncommitted changes from others. Read-committed is the default.

Set isolation at session, transaction, or instance level (Aurora parameter groups).

Syntax:

```sql
SET TRANSACTION transaction_mode [...]
SET TRANSACTION SNAPSHOT snapshot_id
SET SESSION CHARACTERISTICS AS TRANSACTION transaction_mode [...]

-- transaction_mode:
ISOLATION LEVEL { SERIALIZABLE | REPEATABLE READ | READ COMMITTED | READ UNCOMMITTED }
READ WRITE | READ ONLY [ NOT ] DEFERRABLE
```

Examples:

```sql
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- view current isolation level:
SELECT CURRENT_SETTING('TRANSACTION_ISOLATION'); -- Session
SHOW DEFAULT_TRANSACTION_ISOLATION;              -- Instance
```

Use parameter groups to modify the instance-level `default_transaction_isolation`.

**Serializable conflict behavior**: when two transactions update the same row under serializable isolation, the second receives `ERROR: couldn't serialize access due to concurrent update` and its commit rolls back — the application must retry.

## Summary

| Transaction property | SQL Server | Aurora PostgreSQL |
|---|---|---|
| Default isolation level | `READ COMMITTED` | `READ COMMITTED` |
| Initialize transaction syntax | `BEGIN TRAN`/`TRANSACTION` | `SET TRANSACTION` |
| Default isolation mechanism | Pessimistic lock based | Lock based for writes, consistent read for selects |
| Commit transaction | `COMMIT [WORK\|TRAN\|TRANSACTION]` | `COMMIT [WORK\|TRANSACTION]` |
| Rollback transaction | `ROLLBACK [WORK\|TRAN\|TRANSACTION]` | `ROLLBACK [WORK\|TRANSACTION]` |
| Set autocommit off/on | `SET IMPLICIT_TRANSACTIONS OFF\|ON` | `SET AUTOCOMMIT { = \| TO } { ON \| OFF }` |
| ANSI isolation | `REPEATABLE READ \| READ COMMITTED \| READ UNCOMMITTED \| SERIALIZABLE` | same |
| MVCC | `SNAPSHOT` and `READ COMMITTED SNAPSHOT` | `READ COMMITTED SNAPSHOT` |
| Nested transactions | Supported, via `@@trancount` | Not Supported |

## Conversion notes
- **Nested transactions are not supported** in PostgreSQL — replace with savepoints (`SAVEPOINT`/`ROLLBACK TO SAVEPOINT`); `@@trancount` has no equivalent.
- Transaction-start syntax differs: `BEGIN TRAN` → `BEGIN`/`SET TRANSACTION`.
- `READ UNCOMMITTED` silently behaves as `READ COMMITTED`.
- Client tools (e.g., psql) may set autocommit ON by default — verify with `\echo :AUTOCOMMIT`.
- SQL Server SNAPSHOT/READ COMMITTED SNAPSHOT map to PostgreSQL's MVCC behavior.
- Under SERIALIZABLE, code must handle serialization-failure errors and retry.
