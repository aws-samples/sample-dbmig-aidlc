# Temporary Tables

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.temporary.html

**Conversion category:** Assisted (three-star feature compatibility, three-star automation)
**SCT automation:** Creating Tables action code index. PostgreSQL doesn't support GLOBAL temporary tables, can't read across sessions, and drops temp tables at session end.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): temp FK restriction (verified), `GLOBAL` ignored (verified), autovacuum doesn't analyze temp tables, GTT conversion patterns, fixed schema-qualified temp table example.

## Oracle
`CREATE GLOBAL TEMPORARY TABLE` — persistent DDL structure but non-persistent data; no redo on DML. Data is visible only to the inserting session. Oracle 18c adds **private** temporary tables (dropped at session/transaction end).

- Global temp tables store data in the temporary tablespace.
- DDL allowed (`ALTER TABLE`, `DROP TABLE`, `CREATE INDEX`); indexes and triggers supported.
- Cannot be partitioned, clustered, or index-organized; no parallel UPDATE/DELETE/MERGE; no foreign keys.
- DML generates no redo, but generates undo (and redo for the undo).
- `ON COMMIT PRESERVE ROWS` — truncate at session end, persists beyond transaction.
- `ON COMMIT DELETE ROWS` — truncate after each commit (**Oracle default**).
- 12c: session-specific statistics (`DBMS_STATS` pref `GLOBAL_TEMP_TABLE_STATS` = `SHARED`/`SESSION`); temp undo in temp tablespace via `temp_undo_enabled` (TRUE/FALSE).

```sql
CREATE GLOBAL TEMPORARY TABLE EMP_TEMP (
  EMP_ID NUMBER PRIMARY KEY,
  EMP_FULL_NAME VARCHAR2(60) NOT NULL,
  AVG_SALARY NUMERIC NOT NULL)
  ON COMMIT PRESERVE ROWS;

CREATE INDEX IDX_EMP_TEMP_FN ON EMP_TEMP(EMP_FULL_NAME);
INSERT INTO EMP_TEMP VALUES(1, 'John Smith', '5000');
COMMIT;
```

## PostgreSQL
PostgreSQL temp tables are similar but **not global**: the table structure (DDL) is not stored in the database; the temp table is dropped when the session ends. Each session must create its own temp table (private; identical names allowed across sessions). From PostgreSQL 10, partition tables can also be temporary.

- No cross-session data access. `GLOBAL`/`LOCAL` keywords are accepted but have **no effect** (PostgreSQL always creates local, session-isolated tables). `GLOBAL` is deprecated.
- `ON COMMIT PRESERVE ROWS` — **PostgreSQL default** (opposite of Oracle).
- `ON COMMIT DELETE ROWS` — truncate after each commit.

```sql
CREATE GLOBAL TEMPORARY TABLE EMP_TEMP (   -- GLOBAL accepted, ignored
  EMP_ID NUMERIC PRIMARY KEY,
  EMP_FULL_NAME VARCHAR(60) NOT NULL,
  AVG_SALARY NUMERIC NOT NULL)
  ON COMMIT PRESERVE ROWS;

CREATE INDEX IDX_EMP_TEMP_FN ON EMP_TEMP(EMP_FULL_NAME);
INSERT INTO EMP_TEMP VALUES(1, 'John Smith', '5000');
COMMIT;
SELECT * FROM EMP_TEMP;       -- 1 row (temp tables live in the session's pg_temp schema; do not schema-qualify them)
DROP TABLE EMP_TEMP;
```

With `ON COMMIT DELETE ROWS`, a `SELECT` after `COMMIT` returns 0 rows.

### Summary
| Feature | Oracle | Aurora PostgreSQL |
|---|---|---|
| Semantic | Global Temporary Table | Temporary / Temp Table |
| Create | `CREATE GLOBAL TEMPORARY…` | `CREATE TEMPORARY…` / `CREATE TEMP…` |
| Accessible from multiple sessions | Yes | No |
| DDL persists after session end / restart | Yes | No (dropped at session end) |
| Create index | Yes | Yes |
| Foreign key | Yes (to permanent tables) | Only to other temp tables. A temp table cannot reference a permanent table (`constraints on temporary tables may reference only temporary tables`, verified) |
| ON COMMIT default | DELETE ROWS | PRESERVE ROWS |
| ON COMMIT PRESERVE ROWS | Yes | Yes |
| ON COMMIT DELETE ROWS | Yes | Yes |
| ALTER TABLE | Yes | Yes |
| Gather statistics | `dbms_stats.gather_table_stats` | `ANALYZE` |
| 12c GLOBAL_TEMP_TABLE_STATS | `dbms_stats.set_table_prefs` | `ANALYZE` |

## Conversion notes
- Biggest behavioral gap: **default `ON COMMIT`** is reversed — Oracle defaults to DELETE ROWS, PostgreSQL to PRESERVE ROWS. Set the clause explicitly to avoid surprises.
- PostgreSQL temp tables are session-private and dropped at session end; any code relying on a persistent global temp-table definition must `CREATE TEMP TABLE` in each session.
- No cross-session sharing — redesign workflows that read another session's temp data.
- Replace `dbms_stats` calls with `ANALYZE`. **Autovacuum never analyzes temp tables**, so run `ANALYZE temp_table` after filling a large one, or the planner assumes default row counts.
- `CREATE GLOBAL TEMPORARY TABLE` runs on PG 18 but `GLOBAL` is ignored (verified), so converted DDL that only adds `TEMPORARY` silently creates a table that disappears with the session that ran the migration script.

### Conversion patterns for Oracle GTTs (choose per table, record the choice)

1. **Create on first use** (most common): in each procedure that uses the GTT, run
   `CREATE TEMP TABLE IF NOT EXISTS emp_temp (…) ON COMMIT DELETE ROWS;` (keep Oracle's `ON COMMIT` setting).
   Simple, but frequent create/drop churns the system catalog. Avoid it in very hot code paths.
2. **Unlogged permanent table keyed by session**: `CREATE UNLOGGED TABLE emp_temp (sess_id int DEFAULT pg_backend_pid(), …)`, with every query filtered on `sess_id = pg_backend_pid()` (or row-level security doing that) and cleanup at the end of the work. The definition persists like an Oracle GTT, but this is not crash-safe and the data is not visible on replicas. Not safe behind connection poolers that reuse backends across users.
3. **Replace with a CTE or array** when the GTT only passes an intermediate result inside one procedure.

Oracle 18c **private temporary tables** (`ORA$PTT_…`, `ON COMMIT DROP DEFINITION`) → `CREATE TEMP TABLE … ON COMMIT DROP` (verified).
