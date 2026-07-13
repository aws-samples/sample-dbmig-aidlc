# Multi-Version Concurrency Control (MVCC)

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.mvcc.html

**Conversion category:** Automatic (★★★★★ feature compatibility)
**SCT automation:** N/A

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

-- LOCK TABLE (must be inside transaction)
-- Session 1
START TRANSACTION;
LOCK TABLE EMPLOYEES IN EXCLUSIVE MODE;
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
| Lock dictionary views | `v$lock; v$locked_object; v$session_blockers;` | `SHOW OPEN TABLES WHERE in_use = 1;` |
| Lock a table | `BEGIN; LOCK TABLE employees IN SHARE ROW EXCLUSIVE MODE;` | `LOCK TABLE employees READ` |
| Explicit locking | `SELECT * FROM employees WHERE employee_id=102 FOR UPDATE;` | same |
| Explicit locking options | `SELECT ... FOR UPDATE` | `SELECT ... FOR UPDATE` |

- MVCC concept maps cleanly: both avoid reader/writer blocking and avoid lock escalation.
- Biggest behavioral change: MySQL **auto-commits by default** — wrap multi-statement logic in `START TRANSACTION`/`COMMIT` or set `AUTOCOMMIT=OFF`.
- `SELECT ... FOR UPDATE` must run inside an explicit transaction in MySQL.
- Oracle's five table lock modes collapse to MySQL's READ/WRITE; map `SHARE ROW EXCLUSIVE` etc. to `READ`/`WRITE` accordingly.
