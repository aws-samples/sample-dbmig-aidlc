# Target baseline — Aurora PostgreSQL 18

> **Validated on:** Aurora PostgreSQL **18.6** (`aurora_version() = 18.6.1`), Serverless v2, us-west-2, 2026-10-29.
> Every "verified" statement in this playbook was executed on that cluster through the RDS Data API.
> Aurora PostgreSQL 18 versions offered in the Region at validation time: 18.3, 18.4, 18.6.

The original AWS playbook was written for Aurora PostgreSQL 10–13. A new migration should
target the **latest major version** (18). It has the most native Oracle-compatible features
and the longest support window, and it avoids a near-term major upgrade. This file lists
what changed and which conversion defaults follow from it. Topic files carry the details.

## Conversion defaults on PostgreSQL 18 (supersede older playbook advice)

| Oracle construct | Old playbook (PG 10–13) | PG 18 default | Topic file |
|---|---|---|---|
| Procedure | `RETURNS VOID` function | `CREATE PROCEDURE` + `CALL`; `COMMIT` allowed; `OUT` params (PG 14) | `sql-plsql/procedures-and-functions.md` |
| `MERGE` | `INSERT … ON CONFLICT` | native `MERGE` (PG 15), `RETURNING merge_action()` + `NOT MATCHED BY SOURCE` (PG 17) | `sql-plsql/merge-statement.md` |
| Virtual column | trigger / view / stored generated column | `GENERATED ALWAYS AS (…)` **VIRTUAL** (PG 18 default); `STORED` if indexed/unique/FK/UDF | `tables-indexes/virtual-columns.md` |
| `REGEXP_LIKE/COUNT/INSTR/SUBSTR` | emulation | native (PG 15) | `sql-plsql/single-row-and-aggregate-functions.md` |
| `JSON_VALUE/QUERY/EXISTS/TABLE`, `IS JSON` | operators rewrite | native SQL/JSON (PG 16/17) | `special-features/json-support.md` |
| `SYS_GUID()` | `uuid_generate_v1()` (uuid-ossp) | `gen_random_uuid()` / `uuidv7()` (PG 18) | `sql-plsql/single-row-and-aggregate-functions.md` |
| `NUMBER` | SCT default `double precision` | `numeric` (toolkit `datatype-map.yaml`) | `tables-indexes/common-data-types.md` |
| `NUMBER(p,-s)` | unsupported | `numeric(p,-s)` (PG 15) | `tables-indexes/common-data-types.md` |
| Identity | `SERIAL` | `GENERATED … AS IDENTITY` (also on partitioned tables, PG 17) | `sql-plsql/identity-columns-and-serial.md` |
| `CONNECT BY` | recursive CTE | recursive CTE + `SEARCH`/`CYCLE` (PG 14) | `sql-plsql/common-table-expressions.md` |
| `DISABLE NOVALIDATE` constraint | drop / `NOT VALID` | `NOT ENFORCED` (PG 18, CHECK/FK) | `tables-indexes/table-constraints.md` |
| Named `NOT NULL` | `CHECK (x IS NOT NULL)` | named NOT NULL constraint, `NOT VALID` (PG 18) | `tables-indexes/table-constraints.md` |
| `AFTER LOGON` trigger | not supported | `login` event trigger (PG 17) or `ALTER ROLE … SET` | `tables-indexes/triggers.md` |
| Associative array (`INDEX BY`) | restructure | Aurora `collection` extension, or restructure | `sql-plsql/collections-and-bulk-operations.md` |
| Interval partitioning | app code | `pg_partman` 5.4 + `pg_cron` | `physical-storage/table-partitioning-and-inheritance.md` |
| Optimizer hints | drop | drop; `pg_hint_plan` 1.8 or QPM if proven necessary | `performance-tuning/hints-and-query-planning.md` |
| `DBMS_SCHEDULER` | CloudWatch Events + Lambda | `pg_cron` (in-DB) / EventBridge Scheduler + Lambda/Step Functions | `special-features/dbms-scheduler-and-lambda.md` |
| Database link to Oracle | not supported on RDS | `oracle_fdw` 1.2 | `special-features/database-links-dblink-fdw.md` |
| Tablespaces | create them | drop the clauses (logical only on Aurora) | `tables-indexes/tablespaces-and-data-files.md` |

## Still no PostgreSQL equivalent on 18 (verified where testable)

Autonomous transactions, `SAVEPOINT` inside PL/pgSQL, global temporary tables (`GLOBAL` is
ignored), global (cross-partition) indexes, `SPLIT`/`MERGE PARTITION`, interval/automatic-list
partitioning, invisible indexes, IOTs, incremental/`ON COMMIT` materialized-view refresh,
XQuery (`XMLQUERY` is a syntax error), `UTL_FILE` (orafce `utl_file` is permission-denied on
Aurora), `ROWID`/`BFILE`, synonyms, `MODEL`, compound triggers, STARTUP/SHUTDOWN/SERVERERROR
triggers, Oracle Flashback Query, and an in-place flashback/Backtrack (Backtrack is Aurora MySQL only).

## Behavior differences to test for (verified on 18.6)

- `'' IS NULL` is false; `'a' || NULL` is NULL (use `concat`).
- `SELECT … INTO` without `STRICT` does not raise `NO_DATA_FOUND`.
- `GREATEST`/`LEAST` ignore NULLs.
- `substr(s, -n)` does not count from the end.
- `to_date` drops the time; `::timestamp(0)` rounds fractional seconds.
- `now()`/`LOCALTIMESTAMP` are fixed at transaction start.
- `date + interval '1 month'` differs from `ADD_MONTHS` at month end.
- `COMMIT` inside a block with an `EXCEPTION` clause fails, and a `WHEN OTHERS` handler hides the failure.
- Composite `UNIQUE` with NULLs accepts duplicates that Oracle rejects.
- A NULL range-partition key goes only to the `DEFAULT` partition.
- Identifiers over 63 bytes are silently truncated.
- Sequence `MAXVALUE` is limited to bigint, and `CACHE` is per session.

## Aurora PostgreSQL 18.6 platform facts used throughout

- Extensions relevant to Oracle migrations (from `pg_available_extensions`): `orafce` 4.16, `oracle_fdw` 1.2, `aws_s3` 2.0, `aws_lambda` 2.1, `aws_commons` 1.2, `pg_cron` 1.6, `pg_partman` 5.4.3, `pg_hint_plan` 1.8.0, `apg_plan_mgmt` 3.1 (QPM), `collection` 1.1.1, `pg_columnmask` 1.1.0, `hypopg` 1.4.2, `pg_repack` 1.5.3, `pgaudit` 18.0, `pg_stat_statements` 1.12, `postgis` 3.6.3, `vector` 0.8.2, `pgcrypto` 1.4, `dblink`, `postgres_fdw`, `tds_fdw`, `mysql_fdw`, `plv8` 3.2.4, `pg_tle` 1.5.2, `citext`, `pg_trgm`, `pg_bigm`, `bloom`, `btree_gist`, `tablefunc`, `lo`, `uuid-ossp`.
- **Not available:** `file_fdw`, PL/Python, PL/Java, Citus, `pg_ivm`, `pgtt`.
- Preloadable (`shared_preload_libraries`): `auto_explain, orafce, pgaudit, pg_ad_mapping, pg_bigm, pg_similarity, pg_stat_statements, pg_tle, pg_hint_plan, pg_prewarm, plprofiler, pglogical, pg_cron`. QPM is enabled with `rds.enable_plan_management = 1`.
- Defaults: `UTF8` / `en_US.UTF-8` (libc), `password_encryption = scram-sha-256`, `rds.force_ssl = 1`, `ssl_min_protocol_version = TLSv1.2`, `shared_buffers = SUM({DBInstanceClassMemory/12038},-50003)`, `max_connections = LEAST({DBInstanceClassMemory/9531392},5000)`, `random_page_cost = 4`, `jit = off`, `huge_pages = on`. The PostgreSQL 18 `io_method` (async I/O) setting is not exposed.
- The master user is a member of `rds_superuser`, not a superuser.
- Server-side file `COPY` is not supported; use `\copy`/STDIN or `aws_s3`.
- Instance families orderable for 18.6: r5, r6g/r6gd/r6i/r6id, r7g/r7i, r8g/r8gd/r8a, t3/t4g, x2g, plus `db.serverless`.
- Aurora PostgreSQL **Limitless Database** runs on `16.x-limitless` versions only (not 18).
- AWS DMS supports PostgreSQL 17/18 targets from replication engine **3.5.4**.
- CloudWatch **Database Insights** replaces Performance Insights (end of life 2026-07-31).
