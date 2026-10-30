# Transactions for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.transactions.html

**Conversion category:** Assisted (Three star feature compatibility)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected isolation scope (transaction_isolation parameter; SET GLOBAL denied; tx_isolation removed — verified) and the reversed IMPLICIT_TRANSACTIONS mapping; savepoints, SNAPSHOT/RCSI mapping, gap locks, implicit DDL commit (verified), XACT_ABORT, lock timeout.

## SQL Server

A transaction is an all-or-nothing unit of work complying with ACID (Atomic, Consistent, Isolation, Durable). By default SQL Server uses auto-commit/implicit transactions = ON; each statement is its own transaction unless explicitly wrapped.

### Syntax

```sql
BEGIN TRAN | TRANSACTION [<transaction name>]
COMMIT WORK | [ TRAN | TRANSACTION [<transaction name>]]
ROLLBACK WORK | [ TRAN | TRANSACTION [<transaction name>]]
```

ANSI isolation levels (preventing phenomena):

| Isolation level | Dirty reads | Non-repeatable reads | Phantom reads |
|---|---|---|---|
| Read uncommitted | Allowed | Allowed | Allowed |
| Read committed | Disallowed | Allowed | Allowed |
| Repeatable read | Disallowed | Disallowed | Allowed |
| Serializable | Disallowed | Disallowed | Disallowed |

Two isolation implementations: Pessimistic (locking) and Optimistic (MVCC). SQL Server adds read-committed snapshot and snapshot isolation levels for optimistic. Set with:

```sql
SET TRANSACTION ISOLATION LEVEL { READ UNCOMMITTED | READ COMMITTED | REPEATABLE READ | SNAPSHOT | SERIALIZABLE }
```

### Example

```sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
BEGIN TRANSACTION;
INSERT INTO Table1 VALUES (1, 'A');
UPDATE Table2 SET Column1 = 'Done' WHERE KeyColumn = 1;
COMMIT TRANSACTION;
```

## MySQL

Aurora MySQL supports the four SQL:1992 isolation levels. **Default isolation level is `REPEATABLE READ`** with consistent reads (verified on 3.13 and 8.4.8). *(corrected)* Set it per session/transaction, or cluster-wide with the **`transaction_isolation`** parameter in the DB cluster parameter group; `SET GLOBAL` is denied to the master user (error 1227) and `tx_isolation` no longer exists (error 1193) — both verified. On readers set `aurora_read_replica_read_committed` = ON for `READ COMMITTED` reads.

### Syntax

```sql
SET [SESSION] TRANSACTION ISOLATION LEVEL [READ WRITE | READ ONLY] | REPEATABLE READ |
READ COMMITTED | READ UNCOMMITTED | SERIALIZABLE]

-- transaction boundaries
START TRANSACTION WITH CONSISTENT SNAPSHOT | READ WRITE | READ ONLY
-- or
BEGIN [WORK]

COMMIT [WORK] [AND [NO] CHAIN] [[NO] RELEASE]
ROLLBACK [WORK] [AND [NO] CHAIN] [[NO] RELEASE]
ROLLBACK TO SAVEPOINT <logical_name>
SAVEPOINT <logical_name>

SET autocommit = {0 | 1}
```

`WITH CONSISTENT SNAPSHOT` starts a consistent read (same as `START TRANSACTION` + a `SELECT`); doesn't change isolation level. Under `REPEATABLE READ` the snapshot is taken at first read; under `READ COMMITTED` it resets at each consistent read. `READ ONLY` blocks modifications/locks of non-temp tables and enables optimizations (default is `READ WRITE`).

Notes: MySQL 8 adds `innodb_deadlock_detect` toggle; `SELECT … FOR SHARE`/`FOR UPDATE` support `NOWAIT`, `SKIP LOCKED`, `OF tbl_name`. `FOR SHARE` replaces `LOCK IN SHARE MODE` (latter still available).

### Example

```sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
START TRANSACTION;
INSERT INTO Table1 VALUES (1, 'A');
UPDATE Table2 SET Column1 = 'Done' WHERE KeyColumn = 1;
COMMIT;
```

## Conversion notes

- Default isolation differs: SQL Server `READ COMMITTED` vs Aurora MySQL `REPEATABLE READ` (stricter). Apps built for `READ COMMITTED` may need adjustment or set explicitly.
- `BEGIN TRAN`/`BEGIN TRANSACTION` → `START TRANSACTION`.
- `COMMIT`/`ROLLBACK` with `TRAN`/`TRANSACTION` → use `WORK` (or bare). No change if already bare or `WORK`.
- Autocommit: *(corrected)* `SET IMPLICIT_TRANSACTIONS ON` → `SET autocommit = 0`; `OFF` (default) → `autocommit = 1` (default). PyMySQL (used by this toolkit) defaults to autocommit OFF on the client side.
- Aurora MySQL default mode (consistent read for SELECTs, lock-based for writes) ≈ SQL Server `READ COMMITTED SNAPSHOT`.
- Nested transactions NOT supported — starting a new transaction commits the previous one (SQL Server tracks via `@@trancount`). `SAVE TRANSACTION sp` / `ROLLBACK TRANSACTION sp` → `SAVEPOINT sp` / `ROLLBACK TO SAVEPOINT sp`; named transactions (`BEGIN TRAN name`) → drop the name.
- `READ COMMITTED SNAPSHOT` (SQL Server's MVCC default in Azure) ≈ MySQL `READ COMMITTED`; `SNAPSHOT` ≈ `REPEATABLE READ` (there is no `SNAPSHOT` keyword, verified). Under `REPEATABLE READ` InnoDB uses **gap locks**, so batch jobs that ran concurrently on SQL Server can deadlock (error 1213, retry) — consider `READ COMMITTED` for them.
- **DDL commits implicitly**, also inside procedures (verified: `START TRANSACTION; INSERT; CREATE TABLE; ROLLBACK` kept the insert). SQL Server DDL is transactional; review procedures that create tables inside a transaction.
- Error scope: a failing statement is rolled back but the transaction stays open (like SQL Server with `XACT_ABORT OFF`); emulate `XACT_ABORT ON` with `DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END`.
- Functions and triggers cannot `COMMIT`/`ROLLBACK` (error 1422, verified).
- `SET LOCK_TIMEOUT ms` → `SET SESSION innodb_lock_wait_timeout = seconds` (default 50, verified).
- `BEGIN DISTRIBUTED TRANSACTION` → no MSDTC; XA transactions exist but are not usable across Aurora failovers — redesign.
- Aurora MySQL adds transaction chaining (`AND CHAIN`) and release (`AND RELEASE`) — not in SQL Server.

| Property | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Default isolation | `READ COMMITTED` | `REPEATABLE READ` | Aurora default stricter |
| Init transaction | `BEGIN TRAN`/`TRANSACTION` | `START TRANSACTION` | Rewrite required |
| Default mechanism | Pessimistic lock-based | Lock for writes, consistent read for SELECT | ≈ `READ COMMITTED SNAPSHOT` |
| Commit | `COMMIT [WORK\|TRAN\|TRANSACTION]` | `COMMIT [WORK]` | Rewrite `TRAN`/`TRANSACTION`→`WORK` |
| Rollback | `ROLLBACK [WORK\|TRAN\|TRANSACTION]` | `ROLLBACK [WORK]` | Same |
| Autocommit | `SET IMPLICIT_TRANSACTIONS ON\|OFF` | `SET autocommit = 0\|1` | ON ↔ 0 (corrected order) |
| ANSI isolation | RR/RC/RU/Serializable | RR/RC/RU/Serializable | Compatible syntax |
| MVCC | `SNAPSHOT`, `READ COMMITTED SNAPSHOT` | `WITH CONSISTENT SNAPSHOT` | |
| Nested transactions | Supported (`@@trancount`) | Not supported | New txn commits prior |
| Transaction chaining | Not supported | `AND CHAIN` opens new txn | |
| Transaction release | Not supported | `AND RELEASE` disconnects session | |
