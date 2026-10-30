# Temporary Tables for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.temporarytables.html

**Conversion category:** Assisted (Three star feature compatibility)
**SCT automation:** Three star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Replaced the Oracle-GTT comparison with SQL Server #/## semantics; verified no ON COMMIT clause, no FKs (1215) and the 'Can't reopen table' self-join limit (1137); procedure lifetime and workarounds.

## SQL Server

Temporary tables are stored in the `tempdb` system database. Two types:
- **Local** — single `#` prefix; visible only to the current connection; deleted on disconnect.
- **Global** — `##` prefix; visible to any user; deleted when all referencing connections disconnect.

```sql
CREATE TABLE #MyTempTable (col1 INT PRIMARY KEY);
```

## MySQL

The temporary table DDL is not stored in the database. The table is dropped when the session ends.
- **Session-specific** — each session creates its own; identical names allowed across sessions.
- `ON COMMIT` default in MySQL is `ON COMMIT PRESERVE ROWS` (can't be changed); SQL Server default when omitted is `ON COMMIT DELETE ROWS`.

```sql
CREATE TEMPORARY TABLE EMP_TEMP (
    EMP_ID INT PRIMARY KEY,
    EMP_FULL_NAME VARCHAR(60) NOT NULL,
    AVG_SALARY INT NOT NULL);
```

## Conversion notes

| Feature | SQL Server | Aurora MySQL |
|---|---|---|
| Semantic | `#local` temp table / `##global` temp table | Session temporary table |
| Create table | `CREATE TABLE #t (…)` / `SELECT … INTO #t` | `CREATE TEMPORARY TABLE t (…)` / `CREATE TEMPORARY TABLE t AS SELECT …` |
| Accessible from multiple sessions | `##` only | No |
| Dropped when | session (or creating procedure) ends | session ends — **not** when the creating procedure ends; add `DROP TEMPORARY TABLE IF EXISTS` |
| Create index support | Yes | Yes |
| Foreign key support | No (ignored) | No — error 1215 (verified) |
| Referenced twice in one statement (self-join, subquery, CTE) | Yes | **No — error 1137 "Can't reopen table"** (verified) |
| `ON COMMIT` clause | n/a | not supported (syntax error, verified); rows persist across commits |
| Statistics | automatic | `ANALYZE TABLE` |

> Correction: the original table described Oracle global temporary tables (`CREATE GLOBAL TEMPORARY`, `ON COMMIT DELETE ROWS`, `dbms_stats`), which do not apply to SQL Server, and claimed MySQL supports `ON COMMIT DELETE ROWS` and FKs on temporary tables; it supports neither (verified on 3.13 and 8.4.8).

- SQL Server local temp tables (`#`) map to Aurora MySQL session-private `CREATE TEMPORARY TABLE`.
- SQL Server global temp tables (`##`) have no Aurora MySQL equivalent — use standard tables to share data across sessions.
- **#temp self-joins are common in T-SQL and fail in MySQL** (error 1137). Workarounds: create a second temporary table copy (`CREATE TEMPORARY TABLE t2 AS SELECT * FROM t`), use a CTE over the base query instead of the temp table, or use a regular table keyed by `CONNECTION_ID()`.
- Temporary tables in procedures survive the `CALL`; a second call fails with "table already exists" unless the procedure starts with `DROP TEMPORARY TABLE IF EXISTS`.
- Table variables (`DECLARE @t TABLE`) map to temporary tables with the same caveats.
- Temporary tables pin connections behind RDS Proxy.
- On Aurora readers, temporary tables are allowed (they live on the reader's local storage).
