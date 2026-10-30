# Resource Manager and Dedicated Aurora Clusters

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.dedicated.html

**Conversion category:** Manual / architectural (Three-star feature compatibility)
**SCT automation:** N/A. Key difference: distribute load, applications, or users across multiple instances.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): per-role timeouts (`statement_timeout`, PG 17 `transaction_timeout`, `idle_session_timeout`) instead of kill scripts, `pg_blocking_pids`, custom endpoints, Serverless v2 per workload.

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
| Limit parallel runs | `SET max_parallel_workers_per_gather TO x;` (single Gather/Gather Merge node) **OR** `SET max_parallel_workers TO x;` (whole system) |
| Limit number of sessions per consumer group | `ALTER ROLE app_batch CONNECTION LIMIT 10;` (put each consumer group's users in their own role). For *active*-session limits use RDS Proxy / a pooler with a fixed pool size per workload. |
| Restrict max query runtime (`MAX_EST_EXEC_TIME`, `SWITCH_TIME` cancel) | **Declarative, no script:** `ALTER ROLE app_report SET statement_timeout = '5min';` and, PG 17+, `ALTER ROLE app_report SET transaction_timeout = '30min';` (verified on 18.6). Ad hoc: `SELECT pg_cancel_backend(pid) FROM pg_stat_activity WHERE now() - query_start > interval '5 minutes' AND state = 'active';` |
| Limit max idle time for sessions (`MAX_IDLE_TIME`) | `ALTER ROLE app SET idle_session_timeout = '30min';` (PG 14+) |
| Limit idle session holding locks blocking others (`MAX_IDLE_BLOCKER_TIME`) | `ALTER ROLE app SET idle_in_transaction_session_timeout = '10min';` and `lock_timeout` for waiters. For diagnosis, `pg_blocking_pids(pid)` returns the blockers directly, so no `pg_locks` self-join is needed. |
| Instance caging in RAC | Separate applications across Aurora clusters, or read-only workloads across Aurora read replicas in the same cluster |

## Conversion notes
- No direct feature — convert resource governance into **architecture + monitoring scripts**.
- Use **dedicated/right-sized Aurora clusters and read replicas** instead of partitioning one big server.
- Parallelism control maps to `max_parallel_workers_per_gather` / `max_parallel_workers`.
- Session/query/idle/lock limits: prefer the **per-role timeout parameters** (`statement_timeout`, `transaction_timeout`, `idle_session_timeout`, `idle_in_transaction_session_timeout`, `lock_timeout`) over kill scripts. Fall back to scheduled `pg_terminate_backend()` jobs (`pg_cron`) only for rules the parameters cannot express.
- Route workloads with **Aurora custom endpoints** (a named group of reader instances, for example "reporting") so reporting cannot consume the instances that serve OLTP reads.
- **Aurora Serverless v2** per workload gives each consumer group its own CPU/memory envelope that scales independently, the closest analogue to CPU shares per consumer group.
