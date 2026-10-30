# Configuring Server Options

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.configuration.serveroptions.html

**Conversion category:** N/A (One-star feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): corrected `shared_buffers`/`effective_cache_size` formulas, an `sp_configure` → PG 18 mapping table, and the PG 16–18 parameters that replace the PG 10 list.

**Key difference:** Use Cluster and Database/Cluster Parameter Groups.

## SQL Server

SQL Server provides server-level settings affecting all databases and sessions, modified with the `sp_configure` system stored procedure. Server options let you:
- Define hardware utilization — memory management, affinity mask, priority boost, network packet size, soft NUMA.
- Alter run-time global values — recovery interval, remote login timeout, optimize for ad-hoc workloads, cost threshold for parallelism.
- Enable/disable global features — C2 Audit, OLE procedures, CLR procedures, allow trigger recursion.
- Configure global security — server authentication mode, remote access, shell access via `xp_cmdshell`, CLR access level, database chaining.
- Set session defaults — user options, default language, backup compression, fill factor.

Some settings need `RECONFIGURE` to apply; high-risk settings need `RECONFIGURE WITH OVERRIDE`. Advanced options are hidden by default — set `show advanced options` to 1 and run `sp_configure` to view/modify them. (Server audits use the `CREATE`/`ALTER SERVER AUDIT` T-SQL commands.)

### Syntax

```sql
EXECUTE sp_configure <option>, <value>;
```

### Examples

```sql
-- Limit server memory usage to 4 GB
EXECUTE sp_configure 'show advanced options', 1;
RECONFIGURE;
sp_configure 'max server memory', 4096;
RECONFIGURE;

-- Allow command shell access from T-SQL
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1;
RECONFIGURE;

-- View current values
EXECUTE sp_configure
```

## PostgreSQL

In Amazon Aurora PostgreSQL clusters, **Parameter Groups** change cluster-level and database-level parameters. Most PostgreSQL parameters are configurable, but some are disabled and cannot be modified. Because Aurora restricts access to the underlying OS, parameter changes must be made through Parameter Groups. Aurora is a cluster of DB instances, so some parameters apply cluster-wide while others apply to a particular instance.

**Cluster-level parameters** — managed by **cluster parameter groups** (one per Aurora cluster). Examples:
- `wal_buffers` — cluster parameter group.
- `autovacuum` — cluster parameter group.
- `client_encoding` — cluster parameter group.

**Database instance-level parameters** — managed by **database parameter groups** (each instance can have a unique one). Examples:
- `shared_buffers` — memory cache; Aurora PostgreSQL 18 default: `SUM({DBInstanceClassMemory/12038},-50003)` (about two thirds of instance memory).
- `max_connections` — max client connections; AWS-optimized default: `LEAST({DBInstanceClassMemory/9531392},5000)`.
- `authentication_timeout` — max time (seconds) to complete client authentication.
- `superuser_reserved_connections` — reserved connection slots for superusers.
- `effective_cache_size` — informs the optimizer of kernel cache; Aurora PostgreSQL 18 default: `SUM({DBInstanceClassMemory/12038},-50003)`.

`sp_configure` options and their Aurora PostgreSQL 18 counterparts (all present in the `aurora-postgresql18` parameter group family, validated 2026-10-29):

| SQL Server `sp_configure` | Aurora PostgreSQL 18 |
|---|---|
| `max server memory` | instance class / Serverless v2 max ACU (`shared_buffers` is derived from it) |
| `max degree of parallelism` | `max_parallel_workers_per_gather` (per session/role/parameter group), `max_parallel_workers` |
| `cost threshold for parallelism` | `parallel_setup_cost`, `parallel_tuple_cost`, `min_parallel_table_scan_size` |
| `user connections` | `max_connections` (static; default `LEAST({DBInstanceClassMemory/9531392},5000)`) |
| `remote login timeout` / `remote query timeout` | `statement_timeout`, `transaction_timeout` (PG 17), `idle_session_timeout` |
| `xp_cmdshell`, `clr enabled`, `Ole Automation Procedures` | Not available. No OS access; move to Lambda (`aws_lambda`) |
| `c2 audit mode` / Server Audit | `pgaudit` (preload) + CloudWatch Logs export, or Database Activity Streams |
| `nested triggers` / `server trigger recursion` | No switch; guard with `pg_trigger_depth()` |
| `fill factor` | per table/index `WITH (fillfactor = n)` |
| `backup compression default` | N/A; Aurora backups are continuous and storage-level |
| `optimize for ad hoc workloads` | N/A; `plan_cache_mode` controls generic vs custom plans for prepared statements |

Parameters added in PostgreSQL 16–18 that matter on Aurora 18: `transaction_timeout` (17), `debug_parallel_query` (16; replaces `force_parallel_mode`), `autovacuum_worker_slots` and `autovacuum_vacuum_max_threshold` (18), `idle_replication_slot_timeout` (18), `md5_password_warnings` (18), list-valued `log_connections` (18). `wal_consistency_checking` and PostgreSQL 18's `io_method` are not settable on Aurora. TLS is required by default (`rds.force_ssl = 1`).

### Examples

**Create and configure a new parameter group:** RDS console → **Parameter groups** → select DB family from the **Parameter group family** drop-down → for **Type** select the DB parameter group → **Create**. (You cannot edit the default parameter group; create a custom one to apply changes.)

**Modify an existing parameter group:** RDS console → **Parameter groups** → choose the parameter name to edit → **Edit parameters** → change values → **Save changes**.

## Conversion notes
- There is no `sp_configure`/`RECONFIGURE` equivalent — all server-level configuration is done through Aurora **Parameter Groups**.
- Distinguish **cluster parameter groups** (cluster-wide: `wal_buffers`, `autovacuum`, `client_encoding`) from **database parameter groups** (per-instance: `shared_buffers`, `max_connections`, `authentication_timeout`, `superuser_reserved_connections`, `effective_cache_size`).
- Memory-related defaults are computed from `DBInstanceClassMemory` and scale with the DB instance class.
- Some parameters (e.g. `wal_consistency_checking`) cannot be set in Aurora PostgreSQL because Aurora restricts OS-level access.
- The default parameter group is read-only; create a custom group to apply changes, and reboot if required for `pending-reboot` parameters.
