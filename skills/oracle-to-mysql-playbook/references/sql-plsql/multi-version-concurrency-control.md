# Multi-Version Concurrency Control (MVCC)

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.mvcc.html

**Conversion category:** Automatic (★★★★★ feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Fixed the LOCK TABLES example (it used Oracle syntax; LOCK TABLES commits the open transaction), modern lock views, NOWAIT/SKIP LOCKED, WAIT n mapping, 8.4 LOW_PRIORITY removal and no LOCK in procedures, gap locks and deadlock retry — verified on both versions.

## Oracle

Two primary lock types: exclusive and share. Semantics: writers never block readers; readers never block writers; locks are not escalated from row to page/table; users can issue `LOCK TABLE`. Four lock categories: DML, DDL, explicit/manual, system.

**DML locks** — acquired automatically at row and table level by `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `SELECT … FOR UPDATE`. Row locks (TX) held until `COMMIT`/`ROLLBACK`. Table locks (TM): RS (row share), RX (row exclusive), S (share), SRX (share row exclusive), X (exclusive).

| Statement | Row locks | Table mode | RS | RX | S | SRX | X |
|---|---|---|---|---|---|---|---|
| `SELECT … FROM table` | — | none | Y | Y | Y | Y | Y |
| `INSERT INTO table` | Yes | SX | Y | Y | N | N | N |
| `UPDATE table` | Yes | SX | Y | Y | N | N | N |
| `MERGE INTO table` | Yes | SX | Y | Y | N | N | N |
| `DELETE FROM table` | Yes | SX | Y | Y | N | N | N |
| `SELECT … FOR UPDATE OF` | Yes | SX | Y | Y | N | N | N |
| `LOCK TABLE ... ROW SHARE` | | SS | Y | Y | Y | Y | N |
| `... ROW EXCLUSIVE` | | SX | Y | Y | N | N | N |
| `... SHARE` | | S | Y | N | Y | N | N |
| `... SHARE ROW EXCLUSIVE` | | SSX | Y | N | N | N | N |
| `... EXCLUSIVE` | | X | N | N | N | N | N |

**DDL locks** protect schema object definitions during DDL. **Explicit locking**: transaction level (`SET TRANSACTION ISOLATION LEVEL`, `LOCK TABLE`, `SELECT … FOR UPDATE`) or session level (`ALTER SESSION SET ISOLATION LEVEL`). **System locks**: latches, mutexes, internal locks.

```sql
-- LOCK TABLE
-- Session 1
LOCK TABLE EMPLOYEES IN EXCLUSIVE MODE;
-- Session 2 (waits for session 1 COMMIT/ROLLBACK)
UPDATE EMPLOYEES SET SALARY=SALARY+1000 WHERE EMPLOYEE_ID=114;

-- SELECT ... FOR UPDATE
-- Session 1
SELECT * FROM EMPLOYEES WHERE EMPLOYEE_ID=114 FOR UPDATE;
-- Session 2 (waits)
UPDATE EMPLOYEES SET SALARY=SALARY+1000 WHERE EMPLOYEE_ID=114;
```

## MySQL

InnoDB provides MVCC. Like Oracle: read locks don't conflict with write locks (reads never block writes, writes never block reads); no lock escalation to table level. InnoDB stores three hidden fields per row: `DB_TRX_ID`, `DB_ROLL_PTR`, `DB_ROW_ID`.

**Auto-commit:** MySQL auto-commits by default (unlike Oracle). For explicit transactions: use `START TRANSACTION`/`BEGIN` then `COMMIT`/`ROLLBACK`, or set `AUTOCOMMIT=OFF`. `LOCK TABLE` and `SELECT … FOR UPDATE` are supported in explicit transactions.

`LOCK TABLE` has only two table-level modes:
* **READ lock (shared S):** holder reads only; multiple sessions can hold; others may read without acquiring; `READ LOCAL` == `READ` for InnoDB.
* **WRITE lock (exclusive X):** holder reads and writes; no other session can access until released; `LOW_PRIORITY` is deprecated/no-op.

Row-level intention locks: **IS** (intention shared), **IX** (intention exclusive).

| | X | IX | S | IS |
|---|---|---|---|---|
| X | No | No | No | No |
| IX | No | Yes | No | Yes |
| S | No | No | Yes | Yes |
| IS | No | Yes | Yes | Yes |

**Record lock** — locks an index record (e.g., `SELECT id FROM emps WHERE id=50 FOR UPDATE`); always locks index records (InnoDB creates a hidden clustered index if none). **Gap lock** — locks gaps between/around index records (e.g., `WHERE id BETWEEN 50 AND 80 FOR UPDATE` blocks inserting 60). Transaction-level: `SET TRANSACTION ISOLATION LEVEL`, `LOCK TABLE`, `SELECT … FOR UPDATE`. MySQL auto-detects deadlocks and aborts one transaction.

```sql
-- Syntax
LOCK TABLES tbl_name [[AS] alias] lock_type [, ...]
  lock_type: READ [LOCAL] | [LOW_PRIORITY] WRITE

-- LOCK TABLES (note: LOCK TABLES commits any open transaction; it does not join it)
-- Session 1
SET autocommit = 0;
LOCK TABLES EMPLOYEES WRITE;          -- the original showed Oracle's IN EXCLUSIVE MODE syntax
-- Session 2 (waits)
UPDATE EMPLOYEES SET SALARY=SALARY+1000 WHERE EMPLOYEE_ID=114;

-- SELECT ... FOR UPDATE (inside transaction)
-- Session 1
START TRANSACTION;
SELECT * FROM EMPLOYEES WHERE EMPLOYEE_ID=114 FOR UPDATE;
-- Session 2 (waits)
UPDATE EMPLOYEES SET SALARY=SALARY+1000 WHERE EMPLOYEE_ID=114;
```

## Conversion notes

| Description | Oracle | MySQL |
|---|---|---|
| Lock dictionary views | `v$lock; v$locked_object; v$session_blockers;` | `performance_schema.data_locks` / `data_lock_waits`, `sys.innodb_lock_waits`, `information_schema.innodb_trx` (row locks; verified present on 3.13 and 8.4 — `performance_schema` must be ON to populate `data_locks`); `SHOW OPEN TABLES WHERE in_use = 1` for table locks |
| Lock a table | `BEGIN; LOCK TABLE employees IN SHARE ROW EXCLUSIVE MODE;` | `LOCK TABLE employees READ` |
| Explicit locking | `SELECT * FROM employees WHERE employee_id=102 FOR UPDATE;` | same |
| Explicit locking options | `SELECT ... FOR UPDATE` | `SELECT ... FOR UPDATE` |

- MVCC concept maps cleanly: both avoid reader/writer blocking and avoid lock escalation.
- Biggest behavioral change: MySQL **auto-commits by default** — wrap multi-statement logic in `START TRANSACTION`/`COMMIT` or set `AUTOCOMMIT=OFF`.
- `SELECT ... FOR UPDATE` must run inside an explicit transaction in MySQL; under autocommit the lock is released when the statement ends.
- `FOR UPDATE NOWAIT` / `SKIP LOCKED` and `FOR SHARE` are available on Aurora MySQL 3 / 8.4 (verified). Oracle `FOR UPDATE WAIT n` → `SET SESSION innodb_lock_wait_timeout = n` before the statement (default 50 s, verified).
- `LOCK TABLES … LOW_PRIORITY WRITE` is a syntax error on Aurora MySQL 8.4 (verified); 3.x ignores it.
- `LOCK TABLES` is not allowed in stored procedures (error 1314, verified); Oracle procedures that `LOCK TABLE` need `SELECT … FOR UPDATE` on the rows instead, or `GET_LOCK()` named locks.
- **Gap locks:** under the default `REPEATABLE READ`, range scans with `FOR UPDATE` and `UPDATE/DELETE … WHERE` lock gaps and block concurrent inserts — Oracle has no gap locks. Converted batch jobs that ran concurrently on Oracle can deadlock; consider `READ COMMITTED` (no gap locks for most statements) for those sessions.
- Deadlocks are detected automatically (`innodb_deadlock_detect` = ON, verified) and the victim gets error 1213; Oracle raises ORA-00060. Add retry logic. Set `innodb_print_all_deadlocks` = 1 in the parameter group to log every deadlock.
- Oracle's five table lock modes collapse to MySQL's READ/WRITE; map `SHARE ROW EXCLUSIVE` etc. to `READ`/`WRITE` accordingly.
