# Transactions for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.transactions.html

**Conversion category:** Assisted (Three star feature compatibility)
**SCT automation:** Four star automation level

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

Aurora MySQL supports the four SQL:1992 isolation levels. **Default isolation level is `REPEATABLE READ`** with consistent reads. Only **session** scope can be set (no `GLOBAL`), via the `tx_isolation` parameter.

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
- Autocommit: `SET IMPLICIT_TRANSACTIONS OFF|ON` → `SET autocommit = 0|1`.
- Aurora MySQL default mode (consistent read for SELECTs, lock-based for writes) ≈ SQL Server `READ COMMITTED SNAPSHOT`.
- Nested transactions NOT supported — starting a new transaction commits the previous one (SQL Server tracks via `@@trancount`).
- Aurora MySQL adds transaction chaining (`AND CHAIN`) and release (`AND RELEASE`) — not in SQL Server.

| Property | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Default isolation | `READ COMMITTED` | `REPEATABLE READ` | Aurora default stricter |
| Init transaction | `BEGIN TRAN`/`TRANSACTION` | `START TRANSACTION` | Rewrite required |
| Default mechanism | Pessimistic lock-based | Lock for writes, consistent read for SELECT | ≈ `READ COMMITTED SNAPSHOT` |
| Commit | `COMMIT [WORK\|TRAN\|TRANSACTION]` | `COMMIT [WORK]` | Rewrite `TRAN`/`TRANSACTION`→`WORK` |
| Rollback | `ROLLBACK [WORK\|TRAN\|TRANSACTION]` | `ROLLBACK [WORK]` | Same |
| Autocommit | `SET IMPLICIT_TRANSACTIONS OFF\|ON` | `SET autocommit = 0\|1` | |
| ANSI isolation | RR/RC/RU/Serializable | RR/RC/RU/Serializable | Compatible syntax |
| MVCC | `SNAPSHOT`, `READ COMMITTED SNAPSHOT` | `WITH CONSISTENT SNAPSHOT` | |
| Nested transactions | Supported (`@@trancount`) | Not supported | New txn commits prior |
| Transaction chaining | Not supported | `AND CHAIN` opens new txn | |
| Transaction release | Not supported | `AND RELEASE` disconnects session | |
