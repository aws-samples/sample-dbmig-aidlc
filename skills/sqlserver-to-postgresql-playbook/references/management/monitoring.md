# Monitoring features

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.monitoring.html

**Conversion category:** N/A (three-star feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Database Insights replaces Performance Insights, PG 14–18 views (verified), DMV → PostgreSQL mapping, QPM as the Query Store plan-forcing equivalent.

Key difference: Use the Amazon CloudWatch service (see "Monitoring metrics in an Amazon RDS instance").

## SQL Server

SQL Server provides many interfaces to monitor and collect server data (ad-hoc and ongoing collection, root-cause analysis, preventative/reactive actions).

- **New DMVs (SQL Server 2017):** `sys.dm_db_log_stats`, `sys.dm_tran_version_store_space_usage`, `sys.dm_db_log_info`, `sys.dm_db_stats_histogram`, `sys.dm_os_host_info`.
- **SQL Server 2019:** `LIGHTWEIGHT_QUERY_PROFILING` configuration parameter (lightweight query profiling infrastructure, on by default).
- **Windows OS tools:** Windows Scheduler to trigger CMD/PowerShell collection scripts; System Monitor (graphical, WMI performance objects). Performance objects are also reachable from T-SQL via OS-related DMVs; counters cover real-time (CPU) and aggregated history.
- **Extended Events:** lightweight tracing framework (Packages, Targets, Engine, Sessions); managed via SSMS New Session wizard/GUI. Example:

  ```sql
  CREATE EVENT SESSION Locking_Demo
  ON SERVER
      ADD EVENT sqlserver.lock_escalation,
      ADD EVENT sqlserver.lock_timeout
      ADD TARGET package0.etw_classic_sync_target
          (SET default_etw_session_logfile_path = N'C:\ExtendedEvents\Locking\Demo_20180502.etl')
      WITH (MAX_MEMORY=8MB, MAX_EVENT_SIZE=8MB);
  GO
  ```
- **Trace framework / SQL Server Profiler:** predecessor to Extended Events (Extended Events recommended for new work).
- **SSMS extensions:** Activity Monitor, Query Graphical Show Plan, Query Live Statistics, Replication Monitor, Log Shipping Monitor, Standard Performance Reports.
- **T-SQL:** system procedures (`sp_who`, `sp_lock`, `sp_monitor`), built-in functions (`@@CONNECTIONS`, `@@IO_BUSY`, `@@TOTAL_ERRORS`), and `dm_*` dynamic management views/functions in the `sys` schema.
- **Trace flags:** e.g., flag 1204 logs deadlock information (`DBCC TRACEON`).
- **Query Store:** database-level automatic collection of queries, plans, and runtime statistics; can auto-revert plans on performance regression.

## PostgreSQL

Amazon RDS provides a rich monitoring infrastructure for Aurora PostgreSQL clusters/instances via **Amazon CloudWatch** (plus Enhanced Monitoring for OS metrics) and **CloudWatch Database Insights**. Database Insights replaced Performance Insights, which reached end of life on 2026-07-31. PostgreSQL can also be monitored by querying system catalog tables/views.

- PostgreSQL 12: monitor progress of `CREATE INDEX`, `REINDEX`, `CLUSTER`, `VACUUM FULL` via `pg_stat_progress_create_index` and `pg_stat_progress_cluster`.
- PostgreSQL 13: monitor `ANALYZE` via `pg_stat_progress_analyze`; shared memory usage via `pg_shmem_allocations`.
- PostgreSQL 14: `pg_stat_progress_copy`. PostgreSQL 16: `pg_stat_io` (I/O by backend type). PostgreSQL 17: `pg_wait_events` (catalog of wait events, 387 on Aurora 18.6) and `pg_stat_checkpointer` (checkpoint counters moved out of `pg_stat_bgwriter`). PostgreSQL 18: `pg_aios`. All verified on 18.6.

DMV → PostgreSQL mapping:

| SQL Server | Aurora PostgreSQL 18 |
|---|---|
| `sys.dm_exec_sessions` / `sp_who2` | `pg_stat_activity` |
| `sys.dm_exec_requests` (wait type) | `pg_stat_activity.wait_event_type`, `wait_event`; `pg_wait_events` for descriptions |
| `sys.dm_tran_locks` / `sp_lock` | `pg_locks`; blockers: `pg_blocking_pids(pid)` |
| `sys.dm_exec_query_stats` / Query Store runtime stats | `pg_stat_statements` (preloaded by default; `CREATE EXTENSION` per database) |
| Query Store plan forcing | Aurora **Query Plan Management** (`apg_plan_mgmt`, `rds.enable_plan_management = 1`) |
| `sys.dm_db_index_usage_stats` | `pg_stat_user_indexes` (`idx_scan`, PG 16 `last_idx_scan`) |
| `sys.dm_io_virtual_file_stats` | `pg_stat_io`, `pg_statio_user_tables` |
| `sys.dm_db_stats_histogram` | `pg_stats`, `pg_stats_ext` |
| Extended Events / Profiler | `auto_explain`, `log_min_duration_statement`, `pgaudit`, CloudWatch Logs export |
| `DBCC TRACEON (1204/1222)` deadlock graph | deadlocks are always written to the PostgreSQL log; `log_lock_waits = on` |

Example — access CloudWatch Database Insights:
1. In the AWS console, open **CloudWatch** → **Insights** → **Database Insights** (or the **Monitoring** tab of the cluster in the RDS console).
2. Slice DB load by waits, SQL, hosts, users and databases. **Standard** mode is included; **Advanced** mode adds longer retention, execution plans and fleet-level views.

## Conversion notes

- AWS service replacements: Amazon CloudWatch (metrics + alarms), Enhanced Monitoring (OS metrics), CloudWatch Database Insights (DB load / waits / top SQL) replace SSMS Activity Monitor, System Monitor, Profiler/Extended Events, and Query Store.
- DMVs / system procedures largely map to PostgreSQL system catalog views and `pg_stat_*` progress views.
- No direct Query Store equivalent. Combine `pg_stat_statements` (runtime stats), Aurora QPM (plan capture/approval/forcing), Database Insights (history) and `auto_explain` (plans of slow queries).
