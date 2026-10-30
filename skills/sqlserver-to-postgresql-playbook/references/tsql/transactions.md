# Transactions

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.transactions.html

**Conversion category:** Assisted (three-star feature compatibility, three-star automation)
**SCT automation:** Three-star automation level; SCT action code index: Transaction Isolation

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Corrected 'SET AUTOCOMMIT' (no such server parameter, verified) and 'SET TRANSACTION' as start syntax; SNAPSHOT→REPEATABLE READ, RCSI = default READ COMMITTED; verified routine transaction-control limits (no COMMIT in functions, no SAVEPOINT in PL/pgSQL, COMMIT-in-EXCEPTION-block hazard), lock hints, lock/transaction timeouts, 40001/40P01 retries.

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

**Serializable conflict behavior**: when two transactions update the same row under serializable (or repeatable read) isolation, the second receives `ERROR: could not serialize access due to concurrent update` (SQLSTATE 40001) and must be rolled back and retried by the application.

## Summary

| Transaction property | SQL Server | Aurora PostgreSQL |
|---|---|---|
| Default isolation level | `READ COMMITTED` | `READ COMMITTED` |
| Initialize transaction syntax | `BEGIN TRAN`/`TRANSACTION` | `BEGIN` / `START TRANSACTION` (`SET TRANSACTION` only sets the mode of the current one) |
| Default isolation mechanism | Pessimistic lock based | Lock based for writes, consistent read for selects |
| Commit transaction | `COMMIT [WORK\|TRAN\|TRANSACTION]` | `COMMIT [WORK\|TRANSACTION]` |
| Rollback transaction | `ROLLBACK [WORK\|TRAN\|TRANSACTION]` | `ROLLBACK [WORK\|TRANSACTION]` |
| Set autocommit off/on | `SET IMPLICIT_TRANSACTIONS OFF\|ON` | Client-side only: psql `\set AUTOCOMMIT off`, JDBC `setAutoCommit(false)`, psycopg `autocommit` attribute. There is no server `SET AUTOCOMMIT` (verified on 18.6: unrecognized configuration parameter) |
| ANSI isolation | `REPEATABLE READ \| READ COMMITTED \| READ UNCOMMITTED \| SERIALIZABLE` | same |
| MVCC | `SNAPSHOT` and `READ COMMITTED SNAPSHOT` | Always on: `READ COMMITTED` behaves like RCSI (snapshot per statement); `REPEATABLE READ` behaves like `SNAPSHOT` (snapshot per transaction) |
| Nested transactions | `@@TRANCOUNT` counts nesting; only the outer `COMMIT` commits | Not supported; `SAVEPOINT` in SQL, `BEGIN … EXCEPTION … END` sub-blocks in PL/pgSQL |
| Lock wait timeout | `SET LOCK_TIMEOUT ms` | `SET lock_timeout = 'ms'` (default 0 = wait forever) |
| Transaction timeout | none | `transaction_timeout` (PG 17), `idle_in_transaction_session_timeout` |
| Distributed transactions | `BEGIN DISTRIBUTED TRANSACTION` (MSDTC) | Not available: `max_prepared_transactions` is 0 by default on Aurora; redesign with idempotent steps or sagas |

## Transaction control inside routines (verified on Aurora PostgreSQL 18.6)

- `COMMIT`/`ROLLBACK` are allowed only in a **procedure** invoked by `CALL` (or a `DO` block) that is **not** already inside an explicit transaction. In a function they fail with `invalid transaction termination` (SQLSTATE 2D000).
- `SAVEPOINT`, `ROLLBACK TO SAVEPOINT` and `RELEASE` are **not** allowed in PL/pgSQL ("unsupported transaction command in PL/pgSQL"). `SAVE TRAN sp … ROLLBACK TRAN sp` inside T-SQL code → a nested `BEGIN … EXCEPTION WHEN OTHERS THEN … END` block, which rolls back to its start.
- **Hazard:** a `COMMIT` inside a block that has an `EXCEPTION` clause raises an error. If the handler is `WHEN OTHERS`, the error is swallowed and the work since the last commit is lost silently (verified: `INSERT …; COMMIT; EXCEPTION WHEN OTHERS THEN RAISE NOTICE …` keeps nothing). Put transaction control in an outer block with no `EXCEPTION` clause.
- T-SQL pattern `BEGIN TRAN … IF @@ERROR <> 0 ROLLBACK ELSE COMMIT` inside a procedure → drop the explicit `BEGIN TRAN`; let the caller's transaction (or the `CALL`'s implicit one) commit, and raise on error.
- `IF @@TRANCOUNT > 0 ROLLBACK` in a CATCH block → nothing to do: by the time the PL/pgSQL handler runs, the sub-block is already rolled back.
- Procedures that commit cannot be net-effect tested in a rolled-back transaction; see `engines/sqlserver-to-postgresql/checks/non-portable-constructs.md` §12.

## Conversion notes
- **Nested transactions are not supported** in PostgreSQL — replace with savepoints in client SQL, or `BEGIN … EXCEPTION` sub-blocks in PL/pgSQL; `@@trancount` has no equivalent.
- Transaction-start syntax differs: `BEGIN TRAN` → `BEGIN` / `START TRANSACTION`.
- `SET TRANSACTION ISOLATION LEVEL SNAPSHOT` → `REPEATABLE READ`. Table hints `WITH (NOLOCK)` / `READUNCOMMITTED` → remove (readers never block in PostgreSQL); `WITH (UPDLOCK, ROWLOCK)` → `SELECT … FOR UPDATE`; `READPAST` → `FOR UPDATE SKIP LOCKED`; `TABLOCKX` → `LOCK TABLE … IN ACCESS EXCLUSIVE MODE`.
- `READ UNCOMMITTED` silently behaves as `READ COMMITTED`.
- Client tools (e.g., psql) may set autocommit ON by default — verify with `\echo :AUTOCOMMIT`.
- SQL Server SNAPSHOT/READ COMMITTED SNAPSHOT map to PostgreSQL's MVCC behavior.
- Under SERIALIZABLE **and** REPEATABLE READ, code must retry on SQLSTATE `40001` (`could not serialize access due to concurrent update`); also retry deadlocks (`40P01`, the equivalent of SQL Server error 1205).
- `SET XACT_ABORT ON` is PostgreSQL's normal behavior: any error aborts the transaction, and further statements fail with `current transaction is aborted` (25P02) until `ROLLBACK`.
