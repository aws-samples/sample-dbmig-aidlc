# Monitoring features

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.management.monitoring.html

**Conversion category:** Automatic (Three star feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Performance Insights EOL (2026-07-31) → Database Insights; performance_schema off by default (verified); DMV → MySQL view mappings (INNODB_LOCKS removed, verified); trace replacements.

## SQL Server

SQL Server provides many interfaces for monitoring (ad-hoc and ongoing data collection, root-cause analysis, preventative/reactive actions).

SQL Server 2017 dynamic management views: `sys.dm_db_log_stats`, `sys.dm_tran_version_store_space_usage`, `sys.dm_db_log_info`, `sys.dm_db_stats_histogram`, `sys.dm_os_host_info`. SQL Server 2019 adds the `LIGHTWEIGHT_QUERY_PROFILING` configuration parameter (LWP — efficient query performance data, enabled by default).

**Windows OS-level tools:** Windows Scheduler to run script files (CMD/PowerShell) collecting performance data; System Monitor (graphical, via WMI performance objects; also accessible from T-SQL via OS-related DMVs).

**SQL Server Extended Events:** lightweight tracing framework. Components: Packages (containers), Targets (consumers — Event File, Ring Buffer, Event Counters, Histograms), Engine, Sessions. Example:

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

**SQL Server Profiler / Trace framework:** predecessor to Extended Events (Extended Events recommended for new work).

**SSMS monitoring extensions:** Activity Monitor, Query Graphical Show Plan, Query Live Statistics, Replication Monitor, Log Shipping Monitor, Standard Performance Reports.

**T-SQL:** system stored procedures (`sp_who`, `sp_lock`, `sp_monitor`), built-in functions (`@@CONNECTIONS`, `@@IO_BUSY`, `@@TOTAL_ERRORS`), and Dynamic Management Views/functions (`sys.dm_*`).

**Trace flags:** e.g., trace flag 1204 logs deadlock info via `DBCC TRACEON`.

**Query Store:** database-level automatic collection of queries, run plans, and runtime statistics in system tables; can auto-revert plans on performance regression.

## MySQL

Native MySQL monitoring features (InnoDB logging, the Performance Schema) are turned off for Aurora MySQL, so most third-party tools relying on them can't be used (some vendors offer Aurora-specific monitoring).

Amazon RDS provides rich monitoring via **Amazon CloudWatch**.

**CloudWatch Database Insights** — *(updated)* **Amazon RDS Performance Insights reached end of life on 2026-07-31** and was replaced by CloudWatch Database Insights (Standard mode included; Advanced mode adds per-query statistics, execution history and fleet views). It keeps the DB-load / wait-event model described below.

When the **Performance Schema** is on, Performance Insights provides more detail (DB load by detailed wait events); when off, load is categorized by the MySQL process list state. Enabling options:
* Let Performance Insights manage parameters automatically (Performance Schema turns on when you create an instance with Performance Insights enabled; schema-param changes aren't shown in the parameter group but appear in `SHOW GLOBAL VARIABLES`).
* Set the parameters yourself:

| Parameter name | Value |
|---|---|
| `performance_schema` | 1 (Source = engine-default) |
| `performance-schema-consumer-events-waits-current` | ON |
| `performance-schema-instrument` | `wait/%=ON` |
| `performance-schema-consumer-global-instrumentation` | ON |
| `performance-schema-consumer-thread-instrumentation` | ON |

## Conversion notes
- AWS service replacements: SQL Server monitoring (DMVs, Extended Events, Profiler, Activity Monitor, Query Store) → **Amazon CloudWatch**, **CloudWatch Database Insights** (successor to Performance Insights), and **Enhanced Monitoring**.
- Verified on the validation clusters (default Serverless v2 parameter groups, 3.13 and 8.4.8): `performance_schema` = 0, so `performance_schema.events_statements_summary_by_digest` and `performance_schema.processlist` return no rows. It is a static parameter — enable it in the parameter group and reboot before load tests.
- DMV mappings: `sys.dm_exec_requests`/`sessions` → `SHOW PROCESSLIST`, `sys.session`, `information_schema.innodb_trx`; `sys.dm_exec_query_stats` → `events_statements_summary_by_digest`, `sys.statement_analysis`; `sys.dm_tran_locks` → `performance_schema.data_locks`, `sys.innodb_lock_waits` (`information_schema.INNODB_LOCKS` was removed in 8.0, verified); `sys.dm_os_wait_stats` → `performance_schema.events_waits_summary_global_by_event_name`; `sys.dm_db_index_usage_stats` → `sys.schema_unused_indexes`, `sys.schema_index_statistics`.
- Extended Events / Profiler traces → slow query log with `long_query_time = 0` (exported to CloudWatch Logs) or Database Insights Advanced; Advanced Auditing (`server_audit_logging`, off by default, verified) for audit traces.
- Native MySQL monitoring (InnoDB logging, Performance Schema) is disabled by default on Aurora MySQL; Performance Schema can be enabled for richer Performance Insights wait-event detail.
- Many third-party monitoring tools that depend on those native features won't work; use AWS-native tooling.
