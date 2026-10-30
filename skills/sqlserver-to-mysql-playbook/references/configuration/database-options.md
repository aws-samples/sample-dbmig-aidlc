# Configuring Database Options

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.configuration.databaseoptions.html

**Conversion category:** N/A (no feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): SQL Server database options mapped to Aurora MySQL (isolation and snapshot behavior verified).
**Key difference:** SQL Server database options are inapplicable to Aurora MySQL.

## SQL Server

SQL Server provides database-level options set with `ALTER DATABASE … SET`. These let you:
- Set default session options.
- Turn database features on/off (e.g., `SNAPSHOT_ISOLATION`, `CHANGE_TRACKING`, `ENABLE_BROKER`).
- Configure high availability / disaster recovery (e.g., Always On availability groups).
- Configure security/access control (single-user access, offline, read-only).

Syntax:

```sql
ALTER DATABASE { <database name> } SET { <option> [ ,...n ] };
```

Examples:

```sql
-- Read-only and ARITHABORT by default
ALTER DATABASE Demo SET READ_ONLY, ARITHABORT ON;

-- Automatic statistic creation
ALTER DATABASE Demo SET AUTO_CREATE_STATISTICS ON;

-- Take database offline immediately
ALTER DATABASE DEMO SET OFFLINE WITH ROLLBACK IMMEDIATE;
```

## MySQL

In Aurora MySQL, a database is synonymous with a schema, so the notion of database options is **not applicable**.

Aurora MySQL has two settings saved with the database/schema:
- The default character set.
- The default collation for creating new objects.

## Conversion notes

- SQL Server `ALTER DATABASE … SET` options have no Aurora MySQL equivalent — a "database" in Aurora MySQL is just a schema.
- Runtime/feature settings that were database options in SQL Server map instead to Aurora **server system variables** managed via DB cluster and DB parameter groups (see Server Options).
- Only character set and collation defaults are persisted at the schema level in Aurora MySQL.
- For migration considerations, see Server Options.
- Common SQL Server database options and their Aurora MySQL counterparts: `READ_COMMITTED_SNAPSHOT ON` → InnoDB is always MVCC; set `transaction_isolation = READ-COMMITTED` to match SQL Server's read-committed semantics (Aurora default is `REPEATABLE-READ`, verified). `ALLOW_SNAPSHOT_ISOLATION` → `REPEATABLE READ` (there is no `SNAPSHOT` keyword, verified). `RECOVERY FULL/SIMPLE` → n/a (Aurora storage is always durable; binlog only for replication). `AUTO_CREATE/UPDATE_STATISTICS` → `innodb_stats_auto_recalc` (ON) and manual histograms. `COMPATIBILITY_LEVEL` → engine version. `COLLATE` → `ALTER DATABASE … DEFAULT COLLATE` (affects new tables only). `READ_ONLY` → no per-database switch; revoke write privileges. `SINGLE_USER` → no equivalent.
