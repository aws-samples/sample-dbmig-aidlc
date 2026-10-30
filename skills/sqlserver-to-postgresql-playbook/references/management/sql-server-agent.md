# SQL Server Agent and PostgreSQL

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.scheduledlambda.html

**Conversion category:** N/A
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): `pg_cron` is available on Aurora 18 (verified incl. the `schedule_in_database` restriction), EventBridge Scheduler/Step Functions for multi-step jobs.

## SQL Server

SQL Server Agent provides two main functions: scheduling automated maintenance jobs and alerting. Other SQL Server built-in frameworks, such as replication, also rely on SQL Server Agent jobs.

See the related Maintenance Plans and Alerting topics for the job and alert capabilities Agent drives.

## PostgreSQL

Aurora PostgreSQL 18 has two scheduling options (the original playbook said there was none in-engine; `pg_cron` has since become available on Aurora):

**1. `pg_cron` — in-database jobs (verified on Aurora 18.6).** Add `pg_cron` to `shared_preload_libraries` in the cluster parameter group and reboot, then in the `postgres` database:
```sql
CREATE EXTENSION pg_cron;
-- ≈ sp_add_job + sp_add_jobstep + sp_add_schedule (daily at 01:00 UTC)
SELECT cron.schedule('nightly-reindex', '0 1 * * *', $$REINDEX INDEX CONCURRENTLY sales.idx1$$);
UPDATE cron.job SET database = 'appdb' WHERE jobname = 'nightly-reindex';   -- run in another database
SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 20;      -- ≈ sysjobhistory
SELECT cron.unschedule('nightly-reindex');                                  -- ≈ sp_delete_job
```
On Aurora the master user cannot call `cron.schedule_in_database` (permission denied, verified); use `cron.schedule` and then update `cron.job.database` as shown. Schedules are UTC cron expressions (or `'30 seconds'` intervals). Jobs run as the scheduling user.

**2. Amazon EventBridge Scheduler → AWS Lambda / Step Functions — external jobs.** Use this for multi-step jobs with per-step success/failure branching (Step Functions), jobs that call outside the database (files, APIs, mail), and CmdExec/PowerShell/SSIS steps:
```text
EventBridge Scheduler (rate/cron) -> Step Functions / Lambda -> RDS Data API or psycopg -> CALL proc(...)
```

## Conversion notes

- T-SQL job steps that only run SQL/procedures → `pg_cron` (`CALL schema.proc()`). Multi-step jobs with step logic, retries, notifications, or non-SQL steps → EventBridge Scheduler + Step Functions/Lambda.
- `pg_cron` has no job categories, operators, step-level retry or alert-on-failure. Monitor `cron.job_run_details` (or export the PostgreSQL log to CloudWatch and alarm on failures).
- Agent jobs that SQL Server replication or CDC created are not migrated; DMS/logical replication replaces them.
- Replace Agent alerting with Amazon RDS event notifications + Amazon SNS (see Alerting).
- Replace Agent-driven maintenance jobs with RDS automated snapshots and SQL maintenance commands (`VACUUM`, `ANALYZE`, `REINDEX`) — see Maintenance Plans.
- You pay per Lambda invocation, so choose schedule intervals accordingly.
