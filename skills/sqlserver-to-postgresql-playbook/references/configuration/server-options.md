# Configuring Server Options

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.configuration.serveroptions.html

**Conversion category:** N/A (One-star feature compatibility)
**SCT automation:** N/A

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
- `shared_buffers` — memory cache; AWS-optimized default by DB class: `{DBInstanceClassMemory/10922}`.
- `max_connections` — max client connections; AWS-optimized default: `LEAST({DBInstanceClassMemory/9531392},5000)`.
- `authentication_timeout` — max time (seconds) to complete client authentication.
- `superuser_reserved_connections` — reserved connection slots for superusers.
- `effective_cache_size` — informs the optimizer of kernel cache; AWS-optimized default by DB class (RAM): `{DBInstanceClassMemory/10922}`.

New parameters in PostgreSQL 10:
1. `enable_gathermerge` — enables the gather-merge run plan.
2. `max_parallel_workers` — max number of parallel worker processes.
3. `max_sync_workers_per_subscription` — max synchronous workers for a subscription.
4. `wal_consistency_checking` — checks WAL consistency on the standby (cannot be set in Aurora PostgreSQL).
5. `max_logical_replication_workers` — max logical replication worker processes.
6. `max_pred_locks_per_relation` — max records predicate-locked before locking the entire relation.
7. `max_pred_locks_per_page` — max records predicate-locked before locking the entire page.
8. `min_parallel_table_scan_size` — min table size to consider parallel table scan.
9. `min_parallel_index_scan_size` — min table size to consider parallel index scan.

### Examples

**Create and configure a new parameter group:** RDS console → **Parameter groups** → select DB family from the **Parameter group family** drop-down → for **Type** select the DB parameter group → **Create**. (You cannot edit the default parameter group; create a custom one to apply changes.)

**Modify an existing parameter group:** RDS console → **Parameter groups** → choose the parameter name to edit → **Edit parameters** → change values → **Save changes**.

## Conversion notes
- There is no `sp_configure`/`RECONFIGURE` equivalent — all server-level configuration is done through Aurora **Parameter Groups**.
- Distinguish **cluster parameter groups** (cluster-wide: `wal_buffers`, `autovacuum`, `client_encoding`) from **database parameter groups** (per-instance: `shared_buffers`, `max_connections`, `authentication_timeout`, `superuser_reserved_connections`, `effective_cache_size`).
- Memory-related defaults are computed from `DBInstanceClassMemory` and scale with the DB instance class.
- Some parameters (e.g. `wal_consistency_checking`) cannot be set in Aurora PostgreSQL because Aurora restricts OS-level access.
- The default parameter group is read-only; create a custom group to apply changes, and reboot if required for `pending-reboot` parameters.
