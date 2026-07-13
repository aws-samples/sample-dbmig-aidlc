# Monitoring features

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.monitoring.html

**Conversion category:** N/A (three-star feature compatibility)
**SCT automation:** N/A

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

Amazon RDS provides a rich monitoring infrastructure for Aurora PostgreSQL clusters/instances via **Amazon CloudWatch** (plus Enhanced Monitoring for OS metrics) and **AWS Performance Insights**. PostgreSQL can also be monitored by querying system catalog tables/views.

- PostgreSQL 12: monitor progress of `CREATE INDEX`, `REINDEX`, `CLUSTER`, `VACUUM FULL` via `pg_stat_progress_create_index` and `pg_stat_progress_cluster`.
- PostgreSQL 13: monitor `ANALYZE` via `pg_stat_progress_analyze`; shared memory usage via `pg_shmem_allocations`.

Example — access Aurora Performance Insights:
1. In the AWS console, choose **RDS** → **Performance insights**.
2. The dashboard shows current/past performance metrics; choose the period (5 min, 1 hr, 6 hr, 24 hr) and slice by waits, SQL, hosts, users, etc.

Performance Insights is on by default for Aurora clusters; if a cluster has multiple databases, data is aggregated and retained for 24 hours.

## Conversion notes

- AWS service replacements: Amazon CloudWatch (metrics + alarms), Enhanced Monitoring (OS metrics), AWS Performance Insights (DB load / waits / top SQL) replace SSMS Activity Monitor, System Monitor, Profiler/Extended Events, and Query Store.
- DMVs / system procedures largely map to PostgreSQL system catalog views and `pg_stat_*` progress views.
- No direct Query Store equivalent; combine Performance Insights with `pg_stat_*` views and the slow-query log.
