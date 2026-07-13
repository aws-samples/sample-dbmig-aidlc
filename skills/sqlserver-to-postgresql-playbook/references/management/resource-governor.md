# Resource governor features

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.resourcegovernor.html

**Conversion category:** N/A (three-star feature compatibility)
**SCT automation:** N/A

Key difference: Distribute load, applications, or users across multiple instances.

## SQL Server

Resource Governor controls and manages resource consumption — administrators enforce workload limits on CPU, physical I/O, and Memory; configurations are dynamic and changeable in real time. In SQL Server 2019, `REQUEST_MAX_MEMORY_GRANT_PERCENT` (on `CREATE`/`ALTER WORKLOAD GROUP`) changed from integer to float for finer memory control.

Use cases: minimize bottlenecks for SLAs, protect against runaway queries / throttle I/O-intensive operations (e.g., DBCC), and track/control resource-based pricing.

Concepts:
- **Resource Pools** — physical resources (built-in `internal` and `default`; user-defined pools allowed).
- **Workload Groups** — logical containers for similar session requests; resource limit policies are defined here; each belongs to a Resource Pool.
- **Classification** — inspects incoming connections and assigns them to a Workload Group via a user-defined function.

Example:

```sql
-- Enable the Resource Governor
ALTER RESOURCE GOVERNOR RECONFIGURE;

-- Create a Resource Pool
CREATE RESOURCE POOL ReportingWorkloadPool WITH (MAX_CPU_PERCENT = 20);
ALTER RESOURCE GOVERNOR RECONFIGURE;

-- Create a Workload Group
CREATE WORKLOAD GROUP ReportingWorkloadGroup USING poolAdhoc;
ALTER RESOURCE GOVERNOR RECONFIGURE;

-- Create a classifier function
CREATE FUNCTION dbo.WorkloadClassifier()
RETURNS sysname WITH SCHEMABINDING
AS
BEGIN
    RETURN (CASE
        WHEN HOST_NAME() = 'ReportServer' THEN 'ReportingWorkloadGroup'
        ELSE 'Default'
    END)
END;

-- Register the classifier function
ALTER RESOURCE GOVERNOR WITH (CLASSIFIER_FUNCTION = dbo.WorkloadClassifier);
ALTER RESOURCE GOVERNOR RECONFIGURE;
```

## PostgreSQL

PostgreSQL has no built-in equivalent to Resource Governor. Resource Governor existed largely because SQL Server ran on powerful monolithic, per-CPU-licensed servers hosting many applications. With cloud databases the need to maximize a single server is reduced, so a different approach applies:

- Deploy individual Amazon Aurora clusters of varying sizes, each dedicated to a specific application/workload.
- Use read-only Aurora Replicas to offload reporting workloads from the primary.
- Each instance (primary or replica) scales CPU/memory independently via instance type, and has its own endpoint so applications can target specific replicas to segment workloads.
- You can adjust resources/parameters for read-replicas in the same cluster (read-only) to avoid creating an additional cluster.

Examples — create a cluster (RDS → Databases → Create database → follow wizard) and add replicas (RDS → choose cluster → Instance actions → **Create Aurora Replica** → pick instance class → Create).

### Dedicated Aurora PostgreSQL instances — emulating Resource Governor

| Feature (SQL Server) | Amazon Aurora PostgreSQL approach |
|---|---|
| Set max CPU usage for a resource group | Create a dedicated Aurora instance for a specific application. |
| Limit degree of parallelism for specific queries | `SET max_parallel_workers_per_gather TO x;` (set as part of the app's DB connection) |
| Limit parallel runs | `SET max_parallel_workers_per_gather TO 0;` or `SET max_parallel_workers TO x;` (whole system, PostgreSQL 10+) |
| Limit number of active sessions | Detect open connections per app and restrict via DB procedures or the application DAL, e.g.: `select pid from pg_stat_activity where usename in (select usename from pg_stat_activity where state = 'active' group by usename having count(*) > 10) and state = 'active' order by query_Start;` |
| Restrict max query runtime | Terminate long-running sessions: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE now() - pg_stat_activity.query_start > interval '5 minutes';` |
| Limit max idle time for sessions | Terminate idle sessions: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'regress' AND pid <> pg_backend_pid() AND state = 'idle' AND state_change < current_timestamp - INTERVAL '5' MINUTE;` |
| Limit time an idle session holding locks can block others | Terminate blocking idle sessions via a join of `pg_locks` (blocked vs blocking) and `pg_stat_activity`, calling `pg_terminate_backend(blocking_locks.pid)` where the lock is not granted and the blocker's `state_change` is older than the threshold. |

## Conversion notes

- No engine equivalent — replace Resource Governor with workload isolation across multiple Aurora clusters/instances and read replicas (each independently sized).
- Parallelism limits map to `max_parallel_workers_per_gather` / `max_parallel_workers`.
- Session/query/idle limits are not declarative; implement with `pg_stat_activity` + `pg_terminate_backend` in procedures, the application DAL, or scheduled jobs.
- AWS service replacement: Amazon Aurora replicas + Amazon EC2 instance types for resource segmentation.
