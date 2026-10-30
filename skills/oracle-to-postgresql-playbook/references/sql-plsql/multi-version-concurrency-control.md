# Multi-Version Concurrency Control (MVCC)

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.mvcc.html

**Conversion category:** Automatic (Five-star feature compatibility; concurrency model is conceptually equivalent, though syntax for explicit locks/transactions differs)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): session/role-level isolation (corrected), autocommit is client-side, `lock_timeout` for `WAIT n`, `pg_blocking_pids`, VACUUM/bloat versus undo.

## Oracle

Two primary lock types: exclusive and share locks. High-level semantics:
- Writers never block readers; readers never block writers.
- Oracle never escalates locks from row → page → table level (reduces deadlocks).
- Users can issue explicit locks via `LOCK TABLE`.

Lock categories: DML locks, DDL locks, Explicit (manual) locking, and System locks.

**DML locks** preserve integrity of concurrently accessed data:
- **Row Locks (TX):** acquired by `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `SELECT … FOR UPDATE` on a single row. A table lock is also acquired to block conflicting DDL. Held until `COMMIT`/`ROLLBACK`.
- **Table Locks (TM):** automatically acquired by the same DML operations to prevent conflicting DDL.

Row/table lock modes by statement (RS=Row Share, RX=Row Exclusive, S=Share, SRX=Share Row Exclusive, X=Exclusive):

| Statement | Row locks | Table lock mode |
|---|---|---|
| `SELECT … FROM table` | — | none |
| `INSERT INTO table` | Yes | SX |
| `UPDATE table` | Yes | SX |
| `MERGE INTO table` | Yes | SX |
| `DELETE FROM table` | Yes | SX |
| `SELECT … FOR UPDATE OF` | Yes | SX |
| `LOCK TABLE … ROW SHARE MODE` | | SS |
| `LOCK TABLE … ROW EXCLUSIVE MODE` | | SX |
| `LOCK TABLE … SHARE MODE` | | S |
| `LOCK TABLE … SHARE ROW EXCLUSIVE MODE` | | SSX |
| `LOCK TABLE … EXCLUSIVE MODE` | | X |

**DDL locks** protect a schema object's definition during DDL (e.g., `ALTER TABLE … ADD <COLUMN>`).

**Explicit (manual) locking:**
- Transaction level: `SET TRANSACTION ISOLATION LEVEL`, `LOCK TABLE`, `SELECT … FOR UPDATE`
- Session level: `ALTER SESSION SET ISOLATION LEVEL`

**System locks:** latches, mutexes, internal locks.

Examples:

```sql
-- LOCK TABLE
-- Session 1
LOCK TABLE EMPLOYEES IN EXCLUSIVE MODE;
-- Session 2
UPDATE EMPLOYEES SET SALARY=SALARY+1000 WHERE EMPLOYEE_ID=114;
-- Session 2 waits for session 1 to COMMIT or ROLLBACK

-- SELECT ... FOR UPDATE
-- Session 1
SELECT * FROM EMPLOYEES WHERE EMPLOYEE_ID=114 FOR UPDATE;
-- Session 2
UPDATE EMPLOYEES SET SALARY=SALARY+1000 WHERE EMPLOYEE_ID=114;
```

## PostgreSQL

PostgreSQL maintains consistency using MVCC. Like Oracle:
- Read locks don't conflict with write locks; reads never block writes and writes never block reads.
- PostgreSQL does not escalate locks to table level.

### Auto-commit and explicit transactions

Unlike Oracle, **PostgreSQL uses auto-commit by default**. To get Oracle-like (non-auto-commit) behavior:
- Use `START TRANSACTION` (or `BEGIN TRANSACTION`) then `COMMIT`/`ROLLBACK`, or
- Turn autocommit off in the client: `\set AUTOCOMMIT off` in `psql`, `setAutoCommit(false)` in JDBC, `autocommit = False` in psycopg. Autocommit is a client/driver setting; there is no server parameter for it.

With explicit transactions, `LOCK TABLE` and `SELECT … FOR UPDATE` are supported.

### Lock levels

**Table-level lock modes:** ACCESS SHARE, ROW SHARE, ROW EXCLUSIVE, SHARE UPDATE EXCLUSIVE, SHARE, SHARE ROW EXCLUSIVE, EXCLUSIVE, ACCESS EXCLUSIVE.

**Row-level lock modes:** FOR KEY SHARE, FOR SHARE, FOR NO KEY UPDATE, FOR UPDATE.

**Page-level locks:** shared/exclusive locks on shared-buffer pages, released immediately after a row is fetched/updated.

`LOCK TABLE` synopsis:

```sql
LOCK [ TABLE ] [ ONLY ] name [ * ] [, ...] [ IN lockmode MODE ] [ NOWAIT ]
-- lockmode: ACCESS SHARE | ROW SHARE | ROW EXCLUSIVE | SHARE UPDATE EXCLUSIVE
--           | SHARE | SHARE ROW EXCLUSIVE | EXCLUSIVE | ACCESS EXCLUSIVE
```

Notes: there is no `UNLOCK TABLE`; locks release at `COMMIT`/`ROLLBACK`. `LOCK TABLE` must appear after `START TRANSACTION`.

Examples (must run inside a transaction):

```sql
-- LOCK TABLE
-- Session 1
START TRANSACTION;
LOCK TABLE EMPLOYEES IN EXCLUSIVE MODE;
-- Session 2
UPDATE EMPLOYEES SET SALARY=SALARY+1000 WHERE EMPLOYEE_ID=114;

-- SELECT ... FOR UPDATE
-- Session 1
START TRANSACTION;
SELECT * FROM EMPLOYEES WHERE EMPLOYEE_ID=114 FOR UPDATE;
-- Session 2
UPDATE EMPLOYEES SET SALARY=SALARY+1000 WHERE EMPLOYEE_ID=114;
```

### Deadlocks

PostgreSQL detects deadlocks automatically and aborts one transaction. Example deadlock:

```sql
-- Session 1 step1
UPDATE accounts SET balance = balance + 100.00 WHERE acctnum = 11111;
-- Session 2 step2
UPDATE accounts SET balance = balance + 100.00 WHERE acctnum = 22222;
-- Session 2 step3
UPDATE accounts SET balance = balance - 100.00 WHERE acctnum = 11111;
-- Session 1 step4
UPDATE accounts SET balance = balance - 100.00 WHERE acctnum = 22222;
```

Monitor locks via `pg_locks` and `pg_stat_activity`:

```sql
SELECT
block.pid AS block_pid, block_stm.usename AS blocker_user,
block.mode AS block_mode, block.locktype AS block_locktype,
block.relation::regclass AS block_table, block_stm.query AS block_query,
block.GRANTED AS block_granted, waiting.locktype AS waiting_locktype,
waiting_stm.usename AS waiting_user, waiting.relation::regclass AS waiting_table,
waiting_stm.query AS waiting_query, waiting.mode AS waiting_mode,
waiting.pid AS waiting_pid
FROM pg_catalog.pg_locks AS waiting
JOIN pg_catalog.pg_stat_activity AS waiting_stm ON (waiting_stm.pid = waiting.pid)
JOIN pg_catalog.pg_locks AS block
  ON ((waiting."database" = block."database" AND waiting.relation = block.relation)
   OR waiting.transactionid = block.transactionid)
JOIN pg_catalog.pg_stat_activity AS block_stm ON (block_stm.pid = block.pid)
WHERE NOT waiting.GRANTED AND waiting.pid <> block.pid;
```

## Summary

| Description | Oracle | PostgreSQL |
|---|---|---|
| Lock info dictionary | `v$lock; v$locked_object; v$session_blockers;` | `pg_locks`, `pg_stat_activity` |
| Lock a table | `BEGIN; LOCK TABLE employees IN SHARE ROW EXCLUSIVE MODE;` | `LOCK TABLE employees IN SHARE ROW EXCLUSIVE MODE;` |
| Explicit locking | `SELECT * FROM employees WHERE employee_id=102 FOR UPDATE;` | `BEGIN; SELECT * FROM employees WHERE employee_id=102 FOR UPDATE;` |
| Explicit locking options | `SELECT … FOR UPDATE` | `SELECT … FOR KEY SHARE / SHARE / NO KEY UPDATE / UPDATE` |

## Conversion notes

- Concurrency philosophy matches (MVCC, no lock escalation, readers/writers don't block each other) — no redesign needed.
- The biggest behavioral difference: **PostgreSQL defaults to auto-commit**. Oracle defaults to an open transaction. Explicit locking statements (`LOCK TABLE`, `SELECT … FOR UPDATE`) must be wrapped in `START TRANSACTION` in PostgreSQL.
- Isolation can be set per transaction (`BEGIN ISOLATION LEVEL REPEATABLE READ`), per session (`SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL …`, verified to parse on 18.6), or as a default per role/database (`default_transaction_isolation`). Oracle `ALTER SESSION SET ISOLATION_LEVEL = SERIALIZABLE` → the session form.
- Oracle `SELECT … FOR UPDATE WAIT n` → `SET LOCAL lock_timeout = 'n s'` before the `SELECT … FOR UPDATE`. `NOWAIT` and `SKIP LOCKED` map directly (verified).
- Simpler blocker lookup than the `pg_locks` self-join above: `SELECT pid, pg_blocking_pids(pid), wait_event_type, query FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid)) > 0;`
- **Undo vs. dead tuples:** Oracle keeps old row versions in undo. PostgreSQL keeps them in the table until **VACUUM** removes them. Long-running transactions (including idle-in-transaction sessions and forgotten replication slots) prevent cleanup and cause table bloat, the PostgreSQL counterpart of `ORA-01555` risk. Set `idle_in_transaction_session_timeout` and monitor `pg_stat_activity.backend_xmin` age.
- Oracle's `SELECT … FOR UPDATE` locks are recorded on the row itself in both engines. PostgreSQL has no lock escalation, but very large `FOR UPDATE` scans write to every locked tuple, so keep lock sets small.
- Use `pg_locks` + `pg_stat_activity` instead of Oracle's `v$lock`/`v$locked_object`/`v$session_blockers`.
