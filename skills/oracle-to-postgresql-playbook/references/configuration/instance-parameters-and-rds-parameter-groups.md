# Oracle Instance Parameters and Amazon RDS Parameter Groups

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.configuration.parameters.html

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): corrected the `shared_buffers`/`effective_cache_size` formulas, and replaced the PG 10 parameter list with the PG 16–18 parameters that matter for a migration.

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
* `shared_buffers` — memory cache config; AWS-optimized default based on DB class. Aurora PostgreSQL 18 default: `SUM({DBInstanceClassMemory/12038},-50003)` (in 8 kB pages, about 2/3 of instance memory; Aurora does not rely on the OS page cache, so leave this high)
* `max_connections` — max client connections; default optimized by AWS: `LEAST({DBInstanceClassMemory/9531392},5000)`
* `authentication_timeout` — max time (seconds) to complete client authentication
* `superuser_reserved_connections` — reserved connection slots for superusers
* `effective_cache_size` — informs optimizer how much kernel cache exists (controls cost of large index scans); Aurora PostgreSQL 18 default: `SUM({DBInstanceClassMemory/12038},-50003)`

**Parameters added in PostgreSQL 16–18 that matter for a migration** (all present in the `aurora-postgresql18` family, validated on 18.6):
* `transaction_timeout` (17) — caps total transaction time; the closest equivalent to an Oracle resource-profile limit on long transactions.
* `idle_session_timeout` (14) / `idle_in_transaction_session_timeout` — closes idle sessions, like Oracle profile `IDLE_TIME`.
* `debug_parallel_query` (16) — replaces `force_parallel_mode`, which no longer exists. Not modifiable in Aurora parameter groups.
* `autovacuum_worker_slots` (18) and `autovacuum_vacuum_max_threshold` (18) — let autovacuum workers be added without a restart, and cap the dead-tuple threshold so very large tables are vacuumed more often.
* `idle_replication_slot_timeout` (18) — invalidates logical replication slots that stay idle (for example an abandoned DMS CDC slot) before they retain too much WAL.
* `md5_password_warnings` (18) — warns when MD5 passwords are used. MD5 is deprecated in PostgreSQL 18; keep `password_encryption = scram-sha-256` (the default).
* `log_connections` (18) — now a list (`receipt`, `authentication`, `authorization`, `setup_durations`, `all`).
* `rds.force_ssl` — defaults to `1` (TLS required), with `ssl_min_protocol_version = TLSv1.2`.
* `shared_preload_libraries` — Aurora 18 allows `auto_explain`, `orafce`, `pgaudit`, `pg_ad_mapping`, `pg_bigm`, `pg_similarity`, `pg_stat_statements`, `pg_tle`, `pg_hint_plan`, `pg_prewarm`, `plprofiler`, `pglogical`, `pg_cron`.
* Aurora-specific planner/plan-management parameters are prefixed `apg_` / `apg_plan_mgmt.` (Query Plan Management) and `aurora_`.
* `wal_consistency_checking` can't be set in Aurora PostgreSQL.
* Not exposed in Aurora: PostgreSQL 18's asynchronous I/O setting `io_method`. Aurora's storage layer handles I/O differently, so community AIO tuning advice does not apply.

**Create a parameter group:** Sign in to AWS console → RDS → **Parameter groups** → **Create parameter group**. You can't edit the default parameter group, so create a custom one. Choose the **Parameter group family** (database family), set **Type** = **DB Parameter Group**, then **Create**.

**Modify an existing parameter group:** RDS → **Parameter groups** → choose the parameter group name → **Parameter group actions** → **Edit** → change values → **Save changes**.

## Conversion notes

- Oracle's single `ALTER SYSTEM` + SPFILE model becomes two Aurora constructs: **cluster parameter groups** (cluster-wide) and **database parameter groups** (per-instance).
- Oracle's `scope=spfile|memory|both` persistence model has no direct equivalent; parameter group changes may be dynamic or require a reboot (`pending-reboot`).
- Default parameter groups are read-only — always create a custom group to apply changes.
- Several AWS defaults are formulas keyed off `DBInstanceClassMemory` (e.g., `shared_buffers`, `effective_cache_size`, `max_connections`).
- Some parameters cannot be set in Aurora at all (e.g., `wal_consistency_checking`).
