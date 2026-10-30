# Oracle SGA and PGA Memory Sizing and PostgreSQL Memory Buffers

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.configuration.memory.html

**Conversion category:** N/A (config topic) — feature compatibility: two stars
**SCT automation:** N/A. Key difference: different cache names, similar usage.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): corrected the `work_mem` description, updated the instance-class examples, and added Aurora sizing notes.

## Oracle

An Oracle instance allocates several RAM "pools" used as caches: Buffer Cache, Redo Buffer, Java Pool, Shared Pool, Large Pool, and others. These reside in the **System Global Area (SGA)** and are shared across all sessions. Each session also gets a private **Program/Private Global Area (PGA)** for session-private operations (sorting, private SQL cursor elements, etc.).

All Oracle memory parameters are set with `ALTER SYSTEM`; some changes require an instance restart.

**Individual cache parameters:**
* `db_cache_size` — size of cache for database data
* `log_buffer` — cache for redo log buffers until written to disk
* `shared_pool_size` — cache for shared cursors, stored procedures, control structures
* `large_pool_size` — cache for parallel queries and RMAN backup/restore operations
* `Java_pool_size` — cache for Java code and JVM context

**Automatic SGA management** (most common):
* `sga_max_size` — hard-limit maximum size of the SGA
* `sga_target` — soft-limit for the SGA; Oracle sizes individual caches within it

**PGA / session private memory:**
* `pga_aggregate_target` — soft-limit total memory for all sessions combined
* `pga_aggregate_limit` — hard-limit total memory for all sessions combined (Oracle 12c only)

**Unified automatic management** of both SGA and PGA:
* `memory_target` and `memory_max_target` — Oracle auto-balances memory between pools

## PostgreSQL

Important PostgreSQL memory parameters:

| Memory pool parameter | Description |
|---|---|
| `shared_buffers` | Caches database data read from disk. ≈ Oracle Database Buffer Cache |
| `wal_buffers` | Stores WAL (Write-Ahead-Log) records before writing to disk. ≈ Oracle Redo Log Buffer |
| `work_mem` | Memory per sort/hash operation (per plan node, per worker), before spilling to temp files. Hash operations may use `work_mem × hash_mem_multiplier` (default `2` on Aurora PostgreSQL 18). ≈ Oracle PGA work areas (`sort_area_size`/`hash_area_size`) |
| `maintenance_work_mem` | Memory for backend ops such as `VACUUM`, `CREATE INDEX`, `ALTER TABLE ADD FOREIGN KEY` |
| `temp_buffers` | Per-session buffers for reading data from temporary tables |
| Total memory for the cluster | Controlled by choosing the **DB Instance Class** at instance creation |

Cluster-level parameters such as `shared_buffers` and `wal_buffers` are configured via **parameter groups** in the Amazon RDS Management Console.

**View configured values:**

```sql
show shared_buffers;
show work_mem;
show temp_buffers;

-- all parameters
select * from pg_settings;
```

**Session-level change** (no effect on other sessions; lost if its transaction is aborted/rolled back; persists for the session once committed unless overridden):

```sql
SET SESSION work_mem='100MB';
```

**Transaction-local change** (`SET LOCAL`) — affects only the current transaction; after `COMMIT`/`ROLLBACK` the session-level setting takes effect:

```sql
SET LOCAL work_mem='100MB';
```

**Reset to default:**

```sql
RESET work_mem;
```

**Direct update** to `pg_settings`:

```sql
UPDATE pg_settings SET setting = '100MB' WHERE name = 'work_mem';
```

## Conversion notes

Oracle → PostgreSQL mapping (general reference; functionality is not identical):

| Description | Oracle | PostgreSQL |
|---|---|---|
| Memory for caching table data | `db_cache_size` | `shared_buffers` |
| Memory for transaction log records | `log_buffer` | `wal_buffers` |
| Memory for parallel queries | `large_pool_size` | `work_mem` (per worker; each parallel worker gets its own `work_mem`) |
| Java code and JVM | `Java_pool_size` | N/A |
| Max physical memory for the instance | `sga_max_size` or `memory_max_size` | Configured by RDS/Aurora instance class — e.g. `db.r8g.large`: 16 GiB, `db.r8g.xlarge`: 32 GiB; for Aurora Serverless v2, by ACU (about 2 GiB per ACU) |
| Total private memory for all sessions | `pga_aggregate_target` and `pga_aggregate_limit` | `temp_buffers` (temp table reads), `work_mem` (sorts) |
| View all parameters | `SELECT * FROM v$parameter;` | `SELECT * FROM pg_settings;` |
| Configure session-level parameter | `ALTER SESSION SET ...` | `SET SESSION ...` |
| Configure instance-level parameter | `ALTER SYSTEM SET ...` | Configured by parameter groups in the RDS console |

- No PostgreSQL equivalent for Oracle's Java Pool.
- On Aurora you do not set a total memory limit directly — it is determined by the **DB Instance Class**.
- Unlike Oracle's `ALTER SYSTEM`, Aurora instance-level memory parameters must be changed through parameter groups (OS access is restricted).

### Aurora PostgreSQL 18 notes (validated on 18.6)

- Default `shared_buffers` is `SUM({DBInstanceClassMemory/12038},-50003)` 8 kB pages, about two thirds of instance memory. Community advice to set `shared_buffers` to 25% of RAM does not apply to Aurora, which does not use a double-buffering OS page cache.
- `work_mem` is allocated per sort/hash node and per parallel worker, so a single complex query can use several multiples of it. Do not copy a large Oracle `pga_aggregate_target` into `work_mem`. Set a modest global value and raise it per session or per role (`ALTER ROLE etl SET work_mem = '256MB'`) for batch jobs.
- `hash_mem_multiplier` (default `2`) lets hash joins and hash aggregates use more memory than sorts.
- For working sets larger than memory, **Aurora Optimized Reads** instance classes (for example `db.r8gd`/`db.r6gd`, local NVMe) add a tiered cache and put temporary objects on local storage.
- `huge_pages` is `on` and not modifiable in Aurora.
- Track spills with `log_temp_files = 0` and `temp_blks_written` in `pg_stat_statements`. PostgreSQL 18 `EXPLAIN ANALYZE` reports buffer usage by default, which shows spills without adding `BUFFERS`.
