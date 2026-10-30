# Configuring Database Options

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.configuration.databaseoptions.html

**Conversion category:** N/A (One-star feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): per-database `ALTER DATABASE … SET` exists (corrected); option mapping table (READ_ONLY, OFFLINE, RCSI, statistics, CDC; verified).

## SQL Server

SQL Server provides database-level options set with `ALTER DATABASE … SET`. Use these to:
- Set default session options (see Session Options).
- Enable/disable database features such as `SNAPSHOT_ISOLATION`, `CHANGE_TRACKING`, and `ENABLE_BROKER`.
- Configure high availability / disaster recovery (e.g. Always On availability groups).
- Configure security access control — restrict to a single user, set the database offline, or set read-only.

### Syntax

```sql
ALTER DATABASE { <database name> } SET { <option> [ ,...n ] };
```

### Examples

```sql
-- Set read-only and use ARITHABORT by default
ALTER DATABASE Demo SET READ_ONLY, ARITHABORT ON;

-- Use automatic statistic creation
ALTER DATABASE Demo SET AUTO_CREATE_STATISTICS ON;

-- Set a database offline immediately
ALTER DATABASE DEMO SET OFFLINE WITH ROLLBACK IMMEDIATE;
```

## PostgreSQL

Aurora PostgreSQL supports `CREATE SCHEMA` and `CREATE DATABASE` statements. As with SQL Server, an instance hosts multiple databases, which contain multiple schemas. Objects use a three-part name: `<database>.<schema>.<object>`.

Database options correspond to cluster-level parameters managed by AWS **Cluster Parameter Groups**. Some SQL Server equivalent parameters exist at the instance level in the AWS **Database Parameter Group**.

Example — create a database and schema:

```sql
CREATE DATABASE myapp;
CREATE SCHEMA sales;
```

## Conversion notes
- Database options map to AWS **Database Parameter Group**; server options map to AWS **Cluster Parameter Group** (see Server Options).
- PostgreSQL **does** have per-database settings (the original playbook said there was no `ALTER DATABASE … SET` equivalent). `ALTER DATABASE db SET <parameter> = <value>` sets a default for every new session in that database, and parameter groups set cluster/instance defaults. Verified on Aurora 18.6:

| SQL Server `ALTER DATABASE … SET` | PostgreSQL |
|---|---|
| `READ_ONLY` | `ALTER DATABASE db SET default_transaction_read_only = on;` (a session default, not enforcement; combine with privileges) |
| `OFFLINE` / `SINGLE_USER` | `ALTER DATABASE db ALLOW_CONNECTIONS false;` (plus `pg_terminate_backend` for existing sessions) / `CONNECTION LIMIT 1` |
| `READ_COMMITTED_SNAPSHOT ON` / `ALLOW_SNAPSHOT_ISOLATION ON` | Nothing to set: PostgreSQL `READ COMMITTED` is already MVCC (readers never block writers), like RCSI. `REPEATABLE READ` ≈ SQL Server `SNAPSHOT` |
| `AUTO_CREATE/UPDATE_STATISTICS` | autovacuum's auto-analyze (always on by default) |
| `ANSI_NULLS`, `QUOTED_IDENTIFIER`, `ARITHABORT` | Always standard behavior in PostgreSQL; drop |
| `COMPATIBILITY_LEVEL` | No equivalent; behavior follows the engine major version |
| `RECOVERY FULL/SIMPLE` | N/A; Aurora storage handles durability and PITR |
| `CHANGE_TRACKING` / CDC | Logical replication/decoding (`rds.logical_replication = 1`) or AWS DMS CDC |
| `ENABLE_BROKER` | No Service Broker; see `../tsql/service-broker.md` |
| default collation | Set at `CREATE DATABASE … LOCALE_PROVIDER icu ICU_LOCALE '…'`, not changeable later |
- Aurora PostgreSQL uses three-part naming `<database>.<schema>.<object>`, mirroring SQL Server's database/schema/object hierarchy.
