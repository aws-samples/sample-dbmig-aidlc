# Transaction Model

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.transactions.html

**Conversion category:** Assisted (Four-star feature compatibility, four-star automation; PostgreSQL doesn't support `SAVEPOINT`/`ROLLBACK TO SAVEPOINT` inside functions)
**SCT automation:** Four-star automation level; SCT action code index → Transaction Isolation

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): autocommit is a client setting, SAVEPOINT → inner EXCEPTION block, transaction control in procedures, PG 17 `transaction_timeout`, Oracle SERIALIZABLE ≈ PG REPEATABLE READ.

## Oracle

Transactions are atomic logical units enforcing ACID (Atomicity, Consistency, Isolation, Durability).

ANSI/ISO SQL92 isolation levels and the anomalies they permit:

| Isolation level | Dirty reads | Non-repeatable reads | Phantom reads |
|---|---|---|---|
| Read-uncommitted | Permitted | Permitted | Permitted |
| Read-committed | Not permitted | Permitted | Permitted |
| Repeatable read | Not permitted | Not permitted | Permitted |
| Serializable | Not permitted | Not permitted | Not permitted |

Oracle supports **read-committed** (default) and **serializable**, plus a non-standard **read-only** level. Oracle uses MVCC with the System Change Number (SCN) for read consistency.

```sql
-- Transaction-level
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SET TRANSACTION READ ONLY;

-- Session-level
ALTER SESSION SET ISOLATION_LEVEL = SERIALIZABLE;
ALTER SESSION SET ISOLATION_LEVEL = READ COMMITTED;
```

## PostgreSQL

Same SQL92 isolation levels, with implementation differences:

| Isolation level | Dirty reads | Non-repeatable reads | Phantom reads |
|---|---|---|---|
| Read-uncommitted | Permitted but not implemented (acts as read-committed) | Permitted | Permitted |
| Read-committed | Not permitted | Permitted | Permitted |
| Repeatable read | Not permitted | Not permitted | Permitted but not implemented (no phantom reads) |
| Serializable | Not permitted | Not permitted | Not permitted |

PostgreSQL practically uses three levels (read-uncommitted behaves as read-committed). Repeatable-read in PG also prevents phantom reads. Serializable guarantees the result equals some serial execution (repeatable-read does not). Default is **read-committed** (same as Oracle).

PostgreSQL 12+ supports `AND CHAIN` on `COMMIT`/`ROLLBACK` to immediately start a new transaction with the same parameters. PostgreSQL also uses MVCC (snapshot per transaction start time).

Setting isolation in Aurora PostgreSQL — session, transaction, or instance (parameter group):

```sql
-- Transaction
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

-- Session
SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ COMMITTED;
SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL REPEATABLE READ;

-- View
SELECT CURRENT_SETTING('TRANSACTION_ISOLATION'); -- Session
SHOW DEFAULT_TRANSACTION_ISOLATION;              -- Instance
```

Instance-level: alter `default_transaction_isolation` via Aurora parameter group.

Synopsis:

```sql
SET TRANSACTION transaction_mode [...]
SET TRANSACTION SNAPSHOT snapshot_id
SET SESSION CHARACTERISTICS AS TRANSACTION transaction_mode [...]

-- transaction_mode:
ISOLATION LEVEL { SERIALIZABLE | REPEATABLE READ | READ COMMITTED | READ UNCOMMITTED }
READ WRITE | READ ONLY [ NOT ] DEFERRABLE
```

### Feature comparison

| Feature | Oracle | PostgreSQL |
|---|---|---|
| AutoCommit | Off (SQL*Plus); drivers default ON | Client/driver setting. `psql`, JDBC, psycopg and most drivers default to **ON**. Check via `\echo :AUTOCOMMIT` in psql |
| MVCC | Yes | Yes |
| Default isolation | Read-committed | Read-committed |
| Supported isolation | Serializable, Read-only | Repeatable reads, Serializable, Read-only |
| Configure session isolation | Yes | Yes |
| Configure transaction isolation | Yes | Yes |
| Nested transactions | No true nesting (autonomous transactions only) | No — use `SAVEPOINT`, or in PL/pgSQL a `BEGIN … EXCEPTION … END` block (an implicit subtransaction) |
| Autonomous transactions | `PRAGMA AUTONOMOUS_TRANSACTION` | Not supported — `dblink` loopback or redesign |
| Transaction control in procedures | `COMMIT`/`ROLLBACK` anywhere | `COMMIT`/`ROLLBACK` in procedures and `DO` (PG 11+), not in functions or inside blocks with an `EXCEPTION` clause |
| Transaction time limit | Resource profile | `transaction_timeout` (PG 17+), `statement_timeout`, `idle_in_transaction_session_timeout` |
| `SAVEPOINT` support | Yes | Yes |

### Behavior examples

Read-committed: TX1 updates salary 24000→27000 and sees 27000; concurrent TX2 still sees 24000 until both commit; a second TX2 update blocks until TX1 commits, then both see 29000.

Serializable: same setup, but when TX2 tries to `UPDATE` after TX1 commits, it receives `ERROR: could not serialize access due to concurrent update.` and its commit rolls back. Final value reflects TX1's 27000.

## Conversion notes

- Default isolation (read-committed) and MVCC model match Oracle — minimal change for typical code.
- **`SAVEPOINT`/`ROLLBACK TO SAVEPOINT` are not allowed inside PL/pgSQL** (functions or procedures). Convert `SAVEPOINT sp; … EXCEPTION WHEN … THEN ROLLBACK TO sp;` to an inner `BEGIN … EXCEPTION WHEN … THEN … END;` block, which rolls back that block's changes automatically.
- `COMMIT`/`ROLLBACK` inside Oracle procedures: allowed in PostgreSQL procedures called with `CALL`, with the restrictions in `procedures-and-functions.md` (never inside a block with an `EXCEPTION` clause; the error can be swallowed silently).
- Oracle DDL commits implicitly; PostgreSQL DDL is transactional and is rolled back with the transaction.
- `SET TRANSACTION READ ONLY` maps directly. `SERIALIZABLE READ ONLY DEFERRABLE` is a PG option for long consistent reports that never fail with serialization errors.
- No true nested transactions in PG; emulate with `SAVEPOINT`.
- Watch **auto-commit differences**: Oracle keeps a transaction open; psql and other PG clients may auto-commit. Verify client settings before relying on implicit transactions.
- Map `ALTER SESSION SET ISOLATION_LEVEL` → `SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL …`.
- Serializable in PG can raise serialization-failure errors (`40001`) requiring application retry logic. PostgreSQL `SERIALIZABLE` is true serializable (SSI), stricter than Oracle's `SERIALIZABLE`, which is snapshot isolation. Oracle `SERIALIZABLE` code usually maps best to PostgreSQL `REPEATABLE READ`, which is also snapshot isolation. Choose deliberately and record the decision.
- `COMMIT AND CHAIN` / `ROLLBACK AND CHAIN` (PG 12+) start a new transaction with the same characteristics.
