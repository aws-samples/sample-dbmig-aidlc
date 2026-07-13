# Oracle and MySQL monitoring

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.monitoring.html

**Conversion category:** Manual
**SCT automation:** N/A

Feature compatibility: three-star. Key difference: make sure to change table
names in queries when using MySQL.

## Oracle

Oracle exposes its operational state through the **data dictionary** (persisted
internal tables/views) and **dynamic performance views (V$ views)** (real-time,
continuously updated while the instance runs).

**Data dictionary views** — names are prefixed `DBA_*`, `ALL_*`, or `USER_*`
depending on scope (database-level vs. user-level):

- `DBA_TABLES` — all tables in the database
- `DBA_USERS` — all database users
- `DBA_DATA_FILES` — all physical data files
- `DBA_TABLESPACES` — all tablespaces
- `DBA_TAB_COLS` — columns for all tables

```sql
-- List all tables and their owners
SELECT owner, table_name, tablespace_name
FROM   dba_tables
ORDER  BY owner, table_name;
```

**Dynamic performance views (V$)** — real-time instance state: sessions, memory,
job/task progress, SQL execution stats, and other metrics:

- `V$SESSION` — all currently connected sessions
- `V$LOCKED_OBJECT` — objects with active locks
- `V$INSTANCE` — dynamic instance properties
- `V$SESSION_LONG_OPS` — long-running operations (e.g., executing queries)
- `V$MEMORY_TARGET_ADVICE` — advisory on sizing instance memory

```sql
-- Show current sessions
SELECT sid, serial#, username, status, machine
FROM   v$session
WHERE  username IS NOT NULL;
```

Reference: *Static Data Dictionary Views* and *Data Dictionary and Dynamic
Performance Views* in the Oracle documentation.

## MySQL

MySQL retrieves database state two ways, comparable to Oracle's data dictionary
tables and V$ views. Amazon Aurora MySQL additionally provides a **Performance
Insights** console for monitoring/analyzing workloads and troubleshooting.

**Information schema tables** — SQL-standard views describing objects in the
current database. Comparable to Oracle `USER_*` dictionary tables; owned by the
initial database user; stable across MySQL versions.

```sql
-- List tables (equivalent of DBA_TABLES)
SELECT table_schema, table_name, engine
FROM   information_schema.TABLES
ORDER  BY table_schema, table_name;
```

**SHOW command** — information about databases, tables, columns, and server
status. Supports an optional `LIKE` pattern (`%` and `_` wildcards) to filter
output. Includes dynamic views such as `PROCESSLIST` (requires the `PROCESS`
privilege).

```sql
-- Current sessions (equivalent of V$SESSION)
SHOW PROCESSLIST;

-- Filter status variables
SHOW STATUS LIKE '%read%';
```

Reference: *SHOW Statements* and *INFORMATION_SCHEMA Tables* in the MySQL
documentation.

## Conversion notes

- All monitoring is **manual** — rewrite Oracle V$/dictionary queries against the
  MySQL `information_schema`, `performance_schema`, `mysql` system schema, or
  `SHOW` commands. Object names differ, so queries must be changed.
- For Aurora MySQL, prefer **Performance Insights** for workload analysis and
  performance troubleshooting; also leverage `performance_schema` and the `sys`
  schema (curated views over `performance_schema`) for session, lock, IO, and
  statement-level diagnostics.

### Oracle → MySQL equivalence mapping

| Information | Oracle | MySQL |
|---|---|---|
| Database properties | `V$DATABASE` | `pg_database` *(per source; use `SHOW VARIABLES` / `information_schema.SCHEMATA` on MySQL)* |
| Database sessions | `V$SESSION` | `SHOW PROCESSLIST` |
| Database users | `DBA_USERS` | `mysql.user` |
| Database tables | `DBA_TABLES` | `information_schema.TABLES` |
| Database data files | `DBA_DATA_FILES` | `information_schema.FILES` |
| Table columns | `DBA_TAB_COLS` | `information_schema.COLUMNS` |
| Database locks | `V$LOCKED_OBJECT` | `information_schema.INNODB_LOCKS` |
| Currently configured runtime parameters | `V$PARAMETER` | `SHOW GLOBAL VARIABLES` |
| All system statistics | `V$SYSSTAT` | `information_schema.INNODB_METRICS` |
| Privileges on tables | `DBA_TAB_PRIVS` | `information_schema.TABLE_PRIVILEGES` |
| Information about IO operations | `V$SEGSTAT` | `SHOW STATUS LIKE '%read%';` / `SHOW STATUS LIKE '%write%';` |

> Note: the published playbook lists `pg_database` for "Database properties" — a
> carry-over from the PostgreSQL playbook. On MySQL, database properties are read
> via `SHOW VARIABLES` / `information_schema.SCHEMATA`. The rest of the table is
> reproduced verbatim from the source.
