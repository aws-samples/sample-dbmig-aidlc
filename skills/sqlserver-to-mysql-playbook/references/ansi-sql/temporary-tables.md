# Temporary Tables for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.temporarytables.html

**Conversion category:** Assisted (Three star feature compatibility)
**SCT automation:** Three star automation level

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
| Semantic | Global temporary table | Temporary table |
| Create table | `CREATE GLOBAL TEMPORARY…` | `CREATE TEMPORARY…` |
| Accessible from multiple sessions | Yes | No |
| DDL persists after session end/restart | Yes | No (dropped at end of session) |
| Create index support | Yes | Yes |
| Foreign key support | Yes | Yes |
| `ON COMMIT` default | `COMMIT DELETE ROWS` | `ON COMMIT PRESERVE ROWS` |
| `ON COMMIT PRESERVE ROWS` | Yes | Yes |
| `ON COMMIT DELETE ROWS` | Yes | Yes |
| Alter table support | Yes | Yes |
| Gather statistics | `dbms_stats.gather_table_stats` | `ANALYZE` |

- SQL Server local temp tables (`#`) map to Aurora MySQL session-private `CREATE TEMPORARY TABLE`.
- SQL Server global temp tables (`##`) have no Aurora MySQL equivalent — use standard tables to share data across sessions.
