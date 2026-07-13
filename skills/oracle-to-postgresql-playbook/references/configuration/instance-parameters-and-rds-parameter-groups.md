# Oracle Instance Parameters and Amazon RDS Parameter Groups

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.configuration.parameters.html

**Conversion category:** N/A (config topic) — feature compatibility: one star
**SCT automation:** N/A. Key difference: use Cluster and Database/Cluster parameters.

## Oracle

Oracle instance and database-level parameters are configured with `ALTER SYSTEM`. Some take effect dynamically; others require an instance restart.

* All parameters are stored in a binary **Server Parameter file (SPFILE)**.
* Export the binary SPFILE to a text PFILE:
  ```sql
  CREATE PFILE = 'my_init.ora' FROM SPFILE = 's_params.ora';
  ```

**Persistence scope** when changing a parameter:
* `scope=spfile` — applies only after a restart
* `scope=memory` — dynamic, not persistent across restart
* `scope=both` — dynamic and persistent

**Example:**

```sql
ALTER SYSTEM SET QUERY_REWRITE_ENABLED = TRUE SCOPE=BOTH;
```

## PostgreSQL

On Aurora PostgreSQL clusters, **Parameter Groups** are used to change cluster-level and database-level parameters. Most PostgreSQL parameters are configurable, but some are disabled and can't be modified. Because Aurora restricts access to the underlying OS, parameter changes must be made through Parameter Groups. Aurora is a cluster of instances, so some parameters apply to the whole cluster and others to a particular instance.

**Cluster-level parameters** — managed by **cluster parameter groups** (a single cluster parameter group per Aurora cluster). Examples:
* `wal_buffers` — controlled by a cluster parameter group
* `autovacuum` — controlled by a cluster parameter group
* `client_encoding` — controlled by a cluster parameter group

**Database instance-level parameters** — managed by **database parameter groups** (each instance in a cluster can have a unique database parameter group). Examples:
* `shared_buffers` — memory cache config; AWS-optimized default based on DB class: `{DBInstanceClassMemory/10922}`
* `max_connections` — max client connections; default optimized by AWS: `LEAST({DBInstanceClassMemory/9531392},5000)`
* `authentication_timeout` — max time (seconds) to complete client authentication
* `superuser_reserved_connections` — reserved connection slots for superusers
* `effective_cache_size` — informs optimizer how much kernel cache exists (controls cost of large index scans); default optimized by AWS based on DB class (RAM): `{DBInstanceClassMemory/10922}`

**PostgreSQL 10 new parameters:**
* `enable_gathermerge` — enable run plan gather merge
* `max_parallel_workers` — max number of parallel worker processes
* `max_sync_workers_per_subscription` — max synchronous workers for a subscription
* `wal_consistency_checking` — check WAL consistency on standby (can't be set in Aurora PostgreSQL)
* `max_logical_replication_workers` — max logical replication worker processes
* `max_pred_locks_per_relation` — max records predicate-locked before locking the entire relation
* `max_pred_locks_per_page` — max records predicate-locked before locking the entire page
* `min_parallel_table_scan_size` — minimum table size to consider a parallel table scan
* `min_parallel_index_scan_size` — minimum table size to consider a parallel index scan

**Create a parameter group:** Sign in to AWS console → RDS → **Parameter groups** → **Create parameter group**. You can't edit the default parameter group, so create a custom one. Choose the **Parameter group family** (database family), set **Type** = **DB Parameter Group**, then **Create**.

**Modify an existing parameter group:** RDS → **Parameter groups** → choose the parameter group name → **Parameter group actions** → **Edit** → change values → **Save changes**.

## Conversion notes

- Oracle's single `ALTER SYSTEM` + SPFILE model becomes two Aurora constructs: **cluster parameter groups** (cluster-wide) and **database parameter groups** (per-instance).
- Oracle's `scope=spfile|memory|both` persistence model has no direct equivalent; parameter group changes may be dynamic or require a reboot (`pending-reboot`).
- Default parameter groups are read-only — always create a custom group to apply changes.
- Several AWS defaults are formulas keyed off `DBInstanceClassMemory` (e.g., `shared_buffers`, `effective_cache_size`, `max_connections`).
- Some parameters cannot be set in Aurora at all (e.g., `wal_consistency_checking`).
