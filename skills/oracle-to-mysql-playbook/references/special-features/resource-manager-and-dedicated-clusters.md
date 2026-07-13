# Oracle Resource Manager and Dedicated Amazon Aurora MySQL Clusters

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.dedicated.html

**Conversion category:** Manual (three-star feature compatibility) — distribute load, applications, or users across multiple instances.
**SCT automation:** N/A

## Oracle

Oracle Resource Manager manages multiple concurrent workloads under a single database by partitioning server resources. It can guarantee minimum CPU, distribute CPU by percentage, limit degree of parallelism and parallel servers, manage the parallel statement queue, create active session pools, monitor resource usage, kill/limit runaway sessions, cap query runtime, limit idle-session time, switch resource plans by workload, and do instance caging in RAC.

Three concepts: **Consumer Group** (sessions grouped by resource needs — resources are allocated to groups, not sessions), **Resource Plan** (how the database allocates resources to consumer groups; only one active at a time), and **Resource Plan Directive** (associates a consumer group with a plan and specifies allocation). Plans can reference subplans.

Set/disable the active plan (empty string disables):

```sql
ALTER SYSTEM SET RESOURCE_MANAGER_PLAN = 'mydb_plan';
ALTER SYSTEM SET RESOURCE_MANAGER_PLAN = '';
```

Complex plan directive:

```sql
BEGIN
DBMS_RESOURCE_MANAGER.CREATE_PLAN_DIRECTIVE (
  PLAN => 'DAYTIME',
  GROUP_OR_SUBPLAN => 'OLTP',
  COMMENT => 'OLTP group',
  MGMT_P1 => 75);
END;
/
```

## MySQL

Aurora MySQL has no built-in resource manager equivalent. Oracle Resource Manager existed largely because monolithic, per-CPU-licensed Oracle servers consolidated many workloads. In the cloud, deploy **separate, dedicated Aurora clusters** (varying sizes) per application/workload, with read-only Aurora Replicas (up to 15) offloading reporting. Each instance scales CPU/memory independently by instance class, deploys quickly, and exposes its own endpoint so applications can target specific replicas to segment workloads.

Example: replace a single Oracle DB + Resource Manager workload separation with multiple dedicated Aurora databases/clusters. Add a reader in the console: RDS → Databases → select cluster → Actions → Add reader → choose instance class → Create Aurora Replica.

```sql
-- count active (non-idle) sessions for a user
select count(*) from information_schema.processlist
where user='USER_NAME' and COMMAND<>'Sleep';

-- cap query runtime (session level)
SET max_execution_time TO X;

-- idle sessions for a user (sleeping beyond X seconds)
select count(*) from information_schema.processlist
where user='USER_NAME' and COMMAND='Sleep' and TIME > X;
```

## Conversion notes

Mapping of Resource Manager capabilities to Aurora:

| Oracle Resource Manager | Aurora approach |
|---|---|
| Set max CPU for a resource group | Dedicated Aurora instance per application |
| Limit degree of parallelism per query | N/A |
| Limit parallel runs | N/A |
| Limit number of active sessions | Detect via `information_schema.processlist` and throttle in DB procedures or the app DAL |
| Restrict max query runtime | `SET max_execution_time TO X;` |
| Limit max idle time per session | Detect sleeping sessions via `processlist`, throttle in app/DAL |
| Limit idle session holding locks | Detect via `processlist`, throttle in app/DAL |
| Instance caging in RAC | Separate workloads across Aurora clusters / read replicas |

- Resource isolation is achieved architecturally (separate clusters/instances/endpoints) rather than via in-database plans.
- Some fine-grained controls (parallelism limits, parallel-run limits) have no equivalent.
