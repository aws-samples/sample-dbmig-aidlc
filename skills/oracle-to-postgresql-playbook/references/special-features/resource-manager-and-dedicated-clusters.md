# Resource Manager and Dedicated Aurora Clusters

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.dedicated.html

**Conversion category:** Manual / architectural (Three-star feature compatibility)
**SCT automation:** N/A. Key difference: distribute load, applications, or users across multiple instances.

## Oracle

Oracle Resource Manager manages multiple concurrent workloads in a single database by partitioning server resources, avoiding contention and inappropriate allocation. It can:
- Guarantee minimum CPU cycles for certain sessions.
- Distribute CPU by percentage across session groups.
- Limit degree of parallelism / number of parallel servers per user group; manage parallel statement queue order.
- Create active session pools (max concurrent active sessions per group).
- Monitor resource usage via dictionary views; manage runaway sessions; cap query runtime; limit idle connected time.
- Switch resource plans based on workload; manage CPU across instances in RAC (instance caging).

Three concepts:
- **Consumer group** — collection of sessions grouped by resource requirements (resources allocated to groups, not individual sessions).
- **Resource plan** — how the database allocates resources to consumer groups (only one active at a time; can reference subplans).
- **Resource plan directive** — associates a consumer group with a plan and specifies allocation.

```sql
ALTER SYSTEM SET RESOURCE_MANAGER_PLAN = 'mydb_plan';
ALTER SYSTEM SET RESOURCE_MANAGER_PLAN = '';   -- empty string disables

BEGIN
DBMS_RESOURCE_MANAGER.CREATE_PLAN_DIRECTIVE (
PLAN => 'DAYTIME',
GROUP_OR_SUBPLAN => 'OLTP',
COMMENT => 'OLTP group',
MGMT_P1 => 75);
END;
/
```

## PostgreSQL

PostgreSQL has **no built-in resource manager** equivalent. Because of cloud elasticity, the recommended approach is **architectural**: deploy individual, dedicated Amazon Aurora clusters per application/workload (varying sizes), and add read-only **Aurora Replicas** (up to 15) to offload reporting workloads. Oracle's monolithic per-CPU-licensed model drove consolidation; in the cloud, separating workloads onto right-sized, independently scalable instances is preferable. Each instance has its own endpoint, allowing workload segmentation across replicas.

Add a reader via console: RDS → Databases → select cluster → Actions → Add reader → choose instance class → Create Aurora Replica.

### Summary — Resource Manager → Aurora equivalents

| Oracle Resource Manager | Aurora / PostgreSQL approach |
|---|---|
| Set max CPU usage for a resource group | Create a dedicated Aurora instance for the application |
| Limit degree of parallelism for queries | `SET max_parallel_workers_per_gather TO x;` (set on the app's DB connection) |
| Limit parallel runs | `SET max_parallel_workers_per_gather TO x;` (single Gather/Gather Merge node) **OR** `SET max_parallel_workers TO x;` (whole system, PG 10+) |
| Limit number of active sessions | Detect open connections and restrict in DB procedures or app DAL: `select pid from pg_stat_activity where usename in( select usename from pg_stat_activity where state = 'active' group by usename having count(*) > 10) and state = 'active' order by query_Start;` |
| Restrict max query runtime | Terminate long-runners: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE now()-pg_stat_activity.query_start > interval '5 minutes';` |
| Limit max idle time for sessions | `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'regress' AND pid <> pg_backend_pid() AND state = 'idle' AND state_change < current_timestamp - INTERVAL '5' MINUTE;` |
| Limit idle session holding locks blocking others | Terminate the blocking backend by joining `pg_locks` (blocked vs blocking) with `pg_stat_activity` and calling `pg_terminate_backend(blocking_locks.pid)` where `NOT blocked_locks.granted` and the blocked activity's `state_change` exceeds the threshold |
| Instance caging in RAC | Separate applications across Aurora clusters, or read-only workloads across Aurora read replicas in the same cluster |

## Conversion notes
- No direct feature — convert resource governance into **architecture + monitoring scripts**.
- Use **dedicated/right-sized Aurora clusters and read replicas** instead of partitioning one big server.
- Parallelism control maps to `max_parallel_workers_per_gather` / `max_parallel_workers`.
- Session/query/idle/lock limits are emulated by querying `pg_stat_activity` / `pg_locks` and calling `pg_terminate_backend()`, either via scheduled DB procedures or the application data-access layer.
