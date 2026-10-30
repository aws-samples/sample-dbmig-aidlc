# Oracle SGA/PGA Memory Sizing and MySQL Memory Buffers

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.configuration.memory.html

**Conversion category:** N/A (feature compatibility: two stars)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Current instance classes and Serverless v2 sizing (buffer pool verified), information_schema.GLOBAL_VARIABLES removed (verified), corrected log-buffer and PGA mappings, 8.4 dynamic defaults.

**Key difference:** Different cache names, similar usage.

## Oracle

Oracle allocates shared memory pools in the **System Global Area (SGA)** — Buffer Cache, Redo Buffer, Java Pool, Shared Pool, Large Pool, etc. — shared across all sessions. Each session additionally gets a **Program/Private Global Area (PGA)** for private operations (sorting, private SQL cursors). All memory parameters are set with `ALTER SYSTEM`; some changes require an instance restart.

Individual cache parameters:

- `db_cache_size` — cache for database data
- `log_buffer` — cache for redo log buffers until flushed to disk
- `shared_pool_size` — shared cursors, stored procedures, control structures
- `large_pool_size` — parallel queries and RMAN backup/restore
- `Java_pool_size` — Java code and JVM context

Global / automatic management:

- `sga_max_size` — hard limit for SGA size
- `sga_target` — soft limit for SGA and its individual caches
- `pga_aggregate_target` — soft limit for total memory across all sessions
- `pga_aggregate_limit` — hard limit for total session memory (Oracle 12c)
- `memory_target` / `memory_max_target` — single combined limit; Oracle auto-balances SGA and PGA

## MySQL

MySQL uses different memory buffers per storage engine; this covers **InnoDB**. Key parameters:

| Memory pool parameter | Description |
|---|---|
| `innodb_buffer_pool_size` | Area where InnoDB caches table and index data |
| `optimizer_trace_max_mem_size` | Buffer for optimizer traces |
| `binlog_cache_size` | Cache holding changes to the binary log during a transaction |
| `host_cache_size` | Buffer storing data on connections |
| `innodb_ft_cache_size` | Like the buffer pool but for `FULL_TEXT` index data |
| `stored_program_cache` | Cached stored routines per connection |
| `sort_buffer_size` | Sort buffers used while creating an InnoDB index |

Total memory for an Aurora instance is fixed by the **DB instance class** (for example `db.r7g.large` 16 GiB, `db.r7g.xlarge` 32 GiB; the original's r3 classes are retired), or for **Serverless v2** by the current ACU count (about 2 GiB per ACU). The buffer pool follows capacity: on the 0.5–4 ACU validation clusters `innodb_buffer_pool_size` was ~280 MB (verified).

> Note: cluster-level parameters such as `innodb_buffer_pool_size` and `binlog_cache_size` are configured via parameter groups in the RDS console.

### Examples

```sql
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'binlog_cache_size';
SHOW VARIABLES LIKE 'stored_program_cache';

SELECT * FROM performance_schema.global_variables;   -- information_schema.GLOBAL_VARIABLES was removed (error 1109, verified)

SET SESSION sort_buffer_size = 1000000;
```

### Summary mapping (general reference only)

| Description | Oracle | MySQL |
|---|---|---|
| Cache table data | `db_cache_size` | `innodb_buffer_pool_size` |
| Transaction log records | `log_buffer` | `innodb_log_buffer_size` (redo; 16 MB on 3.x, 64 MB on 8.4, verified); `binlog_cache_size` only matters with binary logging on |
| Parallel queries | `large_pool_size` | N/A |
| Java code and JVM | `Java_pool_size` | N/A |
| Max physical memory for instance | `sga_max_size` / `memory_max_size` | Set by RDS/Aurora instance class |
| Total private memory for all sessions | `pga_aggregate_target`, `pga_aggregate_limit` | No aggregate limit: per-session buffers `sort_buffer_size`, `join_buffer_size` (256 KB each, verified), `tmp_table_size`/`temptable_max_ram` × `max_connections`. (`max_digest_length`, listed in the original, is unrelated.) |
| View all parameters | `SELECT * FROM v$parameter;` | `SHOW GLOBAL VARIABLES` / `performance_schema.global_variables` |
| Configure session-level parameter | `ALTER SESSION SET ...` | `SET SESSION ...` |
| Configure instance-level parameter | `ALTER SYSTEM SET ...` | Parameter groups in RDS console |

## Conversion notes

- Oracle's automatic SGA/PGA management (`sga_target`, `memory_target`) has no Aurora equivalent — total RAM is bound to the chosen instance class, not a settable parameter.
- The dominant data cache maps `db_cache_size` → `innodb_buffer_pool_size`; size it via the parameter group, not at the OS level.
- No Aurora equivalents for `large_pool_size` (parallel query) or `Java_pool_size`.
- Cluster-wide memory parameters (`innodb_buffer_pool_size`, `binlog_cache_size`) are set in parameter groups; per-session tuning uses `SET SESSION`.
- Leave `innodb_buffer_pool_size` at the Aurora default formula (about 3/4 of instance memory); Aurora's shared storage means there is no OS file cache to leave room for.
- On Aurora MySQL 8.4 several memory parameters (`temptable_max_ram`, buffer-pool instances) scale with instance size by default (AWS docs); remove fixed values copied from older parameter groups.
- Watch `FreeableMemory` and out-of-memory restarts when raising per-session buffers: they are allocated per connection.
