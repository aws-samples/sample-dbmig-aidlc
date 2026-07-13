# Transaction Model

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.transactions.html

**Conversion category:** Assisted (★★★★ feature compatibility, ★★★★ automation)
**SCT automation:** Action code "Transaction Isolation" — MySQL default is `REPEATABLE READ`; no nested transactions.

## Oracle

Transactions enforce ACID (Atomicity, Consistency, Isolation, Durability). ANSI/ISO SQL92 defines four isolation levels affecting dirty reads, non-repeatable reads, and phantom reads:

| Isolation level | Dirty reads | Non-repeatable reads | Phantom reads |
|---|---|---|---|
| Read-uncommitted | Permitted | Permitted | Permitted |
| Read-committed | Not permitted | Permitted | Permitted |
| Repeatable read | Not permitted | Not permitted | Permitted |
| Serializable | Not permitted | Not permitted | Not permitted |

Oracle supports **read-committed** (default) and **serializable**, plus a non-ANSI **read-only** level. Oracle uses MVCC with the System Change Number (SCN) for read consistency across all sessions.

```sql
-- Transaction-level
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SET TRANSACTION READ ONLY;

-- Session-level
ALTER SESSION SET ISOLATION_LEVEL = SERIALIZABLE;
ALTER SESSION SET ISOLATION_LEVEL = READ COMMITTED;
```

## MySQL

Aurora MySQL supports all four SQL:1992 isolation levels; **default is `REPEATABLE READ`** (stricter than Oracle's `READ COMMITTED`). Only **session** scope can be changed (GLOBAL not supported — like Oracle). Set via `tx_isolation` parameter.

```sql
SET [SESSION] TRANSACTION ISOLATION LEVEL
  [READ WRITE | READ ONLY] |
  REPEATABLE READ | READ COMMITTED | READ UNCOMMITTED | SERIALIZABLE
```

`READ ONLY` transactions cannot modify/lock tables visible to other transactions (can still modify temp tables); enables optimizations. Default is `READ WRITE`.

### Transaction boundaries
```sql
START TRANSACTION [WITH CONSISTENT SNAPSHOT | READ WRITE | READ ONLY]
-- or
BEGIN [WORK]

COMMIT [WORK] [AND [NO] CHAIN] [[NO] RELEASE]
ROLLBACK [WORK] [AND [NO] CHAIN] [[NO] RELEASE]
ROLLBACK TO SAVEPOINT <logical_name>
SAVEPOINT <logical_name>
```

`WITH CONSISTENT SNAPSHOT` starts a consistent read (snapshot) without changing the isolation level. Under `REPEATABLE READ` the snapshot is based on the first read; under `READ COMMITTED` it resets at each consistent read. `AND CHAIN` immediately starts a new transaction (same isolation/access mode); `RELEASE` disconnects the session after the transaction; `NO` suppresses them.

```sql
-- autocommit (default 1)
SET autocommit = {0 | 1}

-- Serializable transaction example
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
START TRANSACTION;
INSERT INTO Table1 VALUES (1, 'A');
UPDATE Table2 SET Column1 = 'Done' WHERE KeyColumn = 1;
COMMIT;
```

> Note: keep `autocommit=1` on both DB and application sides. Some drivers (Python MySQLdb, PyMySQL) turn autocommit OFF by default. MySQL 8 / RDS 8 adds `innodb_deadlock_detect` and `NOWAIT`/`SKIP LOCKED` with `SELECT … FOR SHARE`/`FOR UPDATE`.

## Conversion notes

| Property | Oracle | Aurora MySQL | Comments |
|---|---|---|---|
| Default isolation | `READ COMMITTED` | `REPEATABLE READ` | MySQL stricter — evaluate app needs; may set to `READ COMMITTED` |
| Init transaction | `START TRANSACTION` | `START TRANSACTION` | same |
| Commit | `COMMIT [WORK\|FORCE]` | `COMMIT [WORK]` | rewrite `FORCE`→`WORK` |
| Rollback | `ROLLBACK [WORK\|TO\|FORCE]` | `ROLLBACK [WORK]` | rewrite `TO`/`FORCE`→`WORK` |
| autocommit | `SET AUTOCOMMIT ON\|OFF` (SQL*Plus) | `SET autocommit = 0\|1` | |
| ANSI isolations | all four | all four | compatible syntax |
| MVCC consistent read | `START TRANSACTION \| READ COMMITTED` | `WITH CONSISTENT SNAPSHOT` | |
| Nested transactions | Supported | **Not supported** | starting a new transaction COMMITs the previous one |
| Transaction chaining | Not supported | `AND CHAIN` opens new transaction on completion | |
| Transaction release | Not supported | `RELEASE` disconnects session on completion | |

- Biggest gotcha: MySQL defaults to `REPEATABLE READ`; apps written for Oracle's `READ COMMITTED` may need the level set explicitly.
- No nested transactions — refactor procedures that start inner transactions.
