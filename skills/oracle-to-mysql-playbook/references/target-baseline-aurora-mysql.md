# Target Baseline — Aurora MySQL 8.4 (with Aurora MySQL 3 / MySQL 8.0 differences)

> Framework note (dbmig-aidlc). Not a playbook chapter. This page records the **target-version
> baseline** for both MySQL playbooks (Oracle → MySQL and SQL Server → MySQL). It was written on
> 2026-10-29 and validated on two live, private clusters through the RDS Data API:
> **Aurora MySQL 8.4.8** (MySQL 8.4.8) and **Aurora MySQL 3.13.0** (MySQL 8.0.45), both Serverless v2
> with default parameter groups. Statements marked *verified* were executed on both clusters unless a
> version is named.

The AWS Oracle→Aurora MySQL and SQL Server→Aurora MySQL playbooks were written for Aurora MySQL 1/2
(MySQL 5.6/5.7). Most of their "not supported" statements about CTEs, window functions, roles,
`CHECK` constraints, regular expressions and `JSON_TABLE` are obsolete on both targets below. The
topic files carry a `Reviewed for Aurora MySQL` line naming what changed.

## Which target version

| | **Aurora MySQL 8.4** (recommended for new migrations) | Aurora MySQL 3 |
|---|---|---|
| Community version | MySQL 8.4 LTS | MySQL 8.0 (community end of life April 2026) |
| Latest minor (2026-10) | 8.4.8 | 3.13 (8.0.45); 3.10 (8.0.42) is the Aurora LTS release |
| Aurora end of standard support | April 2032 | 30 April 2028 (3.10 LTS also 30 April 2028) |
| Version numbering | `8.4.x` | `3.xx.y` |
| Parameter group family | `aurora-mysql8.4` | `aurora-mysql8.0` |

Source: [Aurora MySQL release calendars](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraMySQLReleaseNotes/AuroraMySQL.release-calendars.html).
Aurora MySQL 2 (5.7) left standard support on 31 October 2024 and runs only under paid Extended
Support; do not plan new migrations on it.

- Default to **Aurora MySQL 8.4**. Choose Aurora MySQL 3 (prefer 3.10 LTS) only when a dependency
  requires it, for example converting with **AWS DMS Schema Conversion**, whose Aurora MySQL target
  data provider is 8.0.32 only (see *Tooling* below). Record the choice in
  `customer-specific/environment.md`.
- The toolkit's `engines/*-to-mysql/engine.yaml` still says `default_version: "8.0"`. Everything in the
  conversion defaults below works on both versions unless marked **8.4 only** or **3.x only**.
- Aurora MySQL 8.4 has the same Aurora features as the latest version 3 except **fast insert**
  ([AWS docs](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.MySQL84.html)).
  Backtrack, Parallel Query, Global Database, zero-ETL integrations, local write forwarding,
  Serverless v2, Data API, RDS Proxy, S3/Lambda/SageMaker/Comprehend/Bedrock integration are on both
  (verified with `describe-db-engine-versions` and the `AWS_*_ACCESS` roles on both clusters).

## Conversion defaults (both versions unless marked)

| Construct | Default on Aurora MySQL 8.4 / 3 |
|---|---|
| Recursive and non-recursive CTEs | Native `WITH [RECURSIVE]` (verified). Recursion stops at `cte_max_recursion_depth` = **1000** by default (verified); raise it per session for deep hierarchies. |
| Analytic functions | Native window functions `RANK`, `ROW_NUMBER`, `LAG`, `LEAD`, `NTILE`, `FIRST_VALUE`, frames `ROWS/RANGE BETWEEN` (verified). No `PERCENTILE_CONT`/`MEDIAN`, no `KEEP (DENSE_RANK FIRST)`, no `LISTAGG … OVER`. |
| Regular expressions | Native `REGEXP_LIKE/INSTR/SUBSTR/REPLACE` (ICU, verified). **Case follows the collation**: `REGEXP_LIKE('Abc','^a')` = 1 under the default `_ai_ci` collation; pass `'c'` for case-sensitive (verified). |
| Sequences | **No `CREATE SEQUENCE`** (syntax error, verified). `AUTO_INCREMENT` (one per table) or a sequence table + function. |
| Upsert / `MERGE` | **No `MERGE`.** `INSERT … ON DUPLICATE KEY UPDATE` (use the row alias form `AS new` — `VALUES()` in that clause is deprecated) or separate `UPDATE`/`INSERT`/`DELETE`. |
| Set operators | `UNION`, `INTERSECT`, `EXCEPT` (MySQL 8.0.31+, verified; 8.4 hashes them). No `MINUS` keyword. |
| `LATERAL` / `APPLY` | `JOIN LATERAL (…)` (8.0.14+, verified). |
| Row constructors | `VALUES ROW(1,'a'), ROW(2,'b')` table value constructor (verified). |
| `CHECK` constraints | Enforced (verified, error 3819). Before 8.0.16 they were parsed and ignored. |
| Default values | Expression defaults in parentheses: `DEFAULT (now())`, `DEFAULT (uuid())` (verified). |
| Computed columns | `GENERATED ALWAYS AS (…) VIRTUAL\|STORED` (verified). |
| Function-based indexes | Functional key parts `INDEX ((lower(col)))`, descending indexes, invisible indexes (verified). |
| Invisible columns | `col INT INVISIBLE` (8.0.23+, verified). |
| Instant DDL | `ALTER TABLE … ADD/DROP COLUMN, ALGORITHM=INSTANT` (verified on both). |
| Roles | `CREATE ROLE` / `GRANT role TO user` (verified). `activate_all_roles_on_login` is **OFF** (verified): set default roles with `SET DEFAULT ROLE ALL TO user`, or users see no role privileges. |
| JSON | Native `JSON` type, `JSON_TABLE`, `JSON_VALUE … RETURNING`, `JSON_SCHEMA_VALID`, `->`/`->>` on columns, `JSON_ARRAYAGG`/`JSON_OBJECTAGG` (verified). |
| Row locking | `FOR UPDATE SKIP LOCKED` / `NOWAIT`, `FOR SHARE` (verified). |
| Statistics | Histograms `ANALYZE TABLE … UPDATE HISTOGRAM ON col` (verified). **8.4.7+: `AUTO UPDATE` histograms are disabled** and treated as manual (AWS docs); refresh them in a scheduled job. |
| Plans | `EXPLAIN ANALYZE`, `EXPLAIN FORMAT=TREE`; hash joins; optimizer hints `/*+ … */` incl. `SET_VAR`, `MAX_EXECUTION_TIME` (verified). |
| Foreign keys | **8.4 only:** must reference a `PRIMARY KEY` or a full `UNIQUE` key (`restrict_fk_on_non_standard_key=ON`, error 6125, verified). 3.x also accepts an FK to a non-unique index (verified). Convert to 8.4 rules on both. |
| `AUTO_INCREMENT` on `FLOAT`/`DOUBLE` | **8.4: error 1063** (verified); 3.x accepts it. Use integer types. |
| Jobs | `CREATE EVENT` — the event scheduler is **ON** by default on Aurora (verified on both). |

## Behavior differences that bite migrations (verified on both)

- **The default `sql_mode` on Aurora is EMPTY.** The default parameter groups
  (`default.aurora-mysql8.0`, `default.aurora-mysql8.4`) set `sql_mode` to `0`, so
  `@@GLOBAL.sql_mode` is `''` — no strict mode at all (verified with a direct client connection on
  3.13.0 and 8.4.8, 2026-10-30). Community MySQL 8.x defaults to
  `ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION`.
  *(Corrected 2026-10-30: this file said "only `STRICT_TRANS_TABLES`". The RDS Data API sets
  `STRICT_TRANS_TABLES` for its own sessions, which is what the first check saw.)*
  With the Aurora default, an application connection gets silent data changes (all verified on both):
  - a too-long string is **truncated** (`'toolongvalue'` → `'toolo'` in `VARCHAR(5)`), warning only;
  - an invalid date such as `'2024-02-30'` is stored as **`0000-00-00`**, warning only;
  - in a multi-row `INSERT`, a `NULL` for a `NOT NULL` column becomes **`0` / `''`**, warning only
    (a single-row insert still fails with 1048);
  - `'12abc'` into an `INT` column stores **12**; `SELECT 1/0` returns **NULL**;
  - `SELECT count(*), id FROM t` without `GROUP BY id` runs and returns an arbitrary `id`.
  Oracle and SQL Server raise an error in each case. Set `sql_mode` in a custom **cluster parameter
  group** before testing and cutover
  (`ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION`;
  verified: then `'2024-02-30'` fails with 1292 and a too-long value with 1406), and add
  `PIPES_AS_CONCAT` only if the converted code relies on `||`. Without it, `'a' || 'b'` is a logical
  OR and returns `0` (verified). `dbmig` sets this strict mode on its own sessions (override with
  `sql_mode:` in `connections.yaml`), and `dbmig test-connection` warns when the server's global
  mode is not strict, so the load and tests fail loudly even before the parameter group is fixed.
- **Collation:** default `utf8mb4` / `utf8mb4_0900_ai_ci` — case- **and accent**-insensitive
  (`'abc' = 'ABC'` → 1), and **NO PAD**: trailing spaces are significant (`'a ' = 'a'` → 0, verified).
  Oracle `CHAR` comparisons and SQL Server comparisons ignore trailing spaces; Oracle comparisons are
  case-sensitive. Choose `utf8mb4_0900_as_cs` or `utf8mb4_bin` columns where Oracle case semantics
  must hold.
- A **column-level** `col … REFERENCES t (c)` clause is parsed and silently ignored — no foreign key is created
  (verified). Declare FKs as table-level `FOREIGN KEY (…) REFERENCES …` clauses.
- `FOREIGN KEY … ON DELETE SET DEFAULT` is accepted and shown by `SHOW CREATE TABLE`, but InnoDB enforces it as
  `RESTRICT`: the parent delete fails with error 1451 (verified). Treat `SET DEFAULT` as unsupported.
- `CREATE TABLE … ENGINE=FEDERATED` silently creates an **InnoDB** table, even with `NO_ENGINE_SUBSTITUTION`
  (verified). FEDERATED is not available on Aurora; check `information_schema.tables.ENGINE` after DDL.
- `NCHAR`/`NVARCHAR` columns are `utf8mb3` and reject 4-byte characters (error 1366); map Oracle/SQL Server national types to `utf8mb4` `CHAR`/`VARCHAR`.
- **Empty string is not NULL** (`'' IS NULL` → 0); `CONCAT('a', NULL)` → NULL, `CONCAT_WS` skips NULLs.
- **Integer division and rounding:** `1/3` = `0.3333` (`div_precision_increment` = 4); `ROUND(-2.5)` = -3
  (half away from zero, like Oracle); `MOD(-7,3)` = -1. `BIGINT` overflow raises error 1690.
- **`GROUP_CONCAT` truncates at `group_concat_max_len` = 1024 bytes** silently. Raise it (session or
  parameter group) for `LISTAGG`/`STRING_AGG` conversions.
- **DDL commits implicitly**, also inside a procedure: `START TRANSACTION; INSERT …; CREATE TABLE …;
  ROLLBACK` keeps the inserted row (verified).
- Stored functions and triggers cannot `COMMIT` (error 1422) or use dynamic SQL (`PREPARE`, error 1336)
  (verified). Procedures can do both.
- Triggers are row-level only: `FOR EACH STATEMENT` is a syntax error (verified); no `INSTEAD OF`
  triggers. Multiple triggers per event are ordered with `FOLLOWS`/`PRECEDES` (verified).
- Recursive stored procedures are off: `max_sp_recursion_depth` = 0 (verified).
- `SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = …, MYSQL_ERRNO = 50001` and handlers with
  `GET DIAGNOSTICS` work (verified) — the mapping target for `RAISE_APPLICATION_ERROR` / `THROW`.
- Time: `system_time_zone` is UTC on Aurora (verified). `NOW()` is statement start, `SYSDATE()` is
  call time (verified differences in microseconds).
- `performance_schema` is **OFF** by default on Serverless v2 with the default parameter group
  (verified). Turn it on (static parameter, needs reboot) before relying on
  `performance_schema`/`sys` views or Database Insights SQL-level detail.
- `max_connections` scales with capacity (135 at 0.5–4 ACU, verified). Size it, or use RDS Proxy, for
  migrated connection-heavy applications.
- InnoDB full-text search uses `innodb_ft_min_token_size` = 3 (verified); words shorter than that are
  not indexed.

## Aurora MySQL 8.4 vs 3 differences (verified unless noted)

| Area | Aurora MySQL 3 | Aurora MySQL 8.4 |
|---|---|---|
| Authentication | `default_authentication_plugin` = `mysql_native_password` | `default_authentication_plugin` removed; `authentication_policy` = `*:caching_sha2_password`; `mysql_native_password` stays loaded (unlike community 8.4) so old drivers keep working. Use a driver that supports `caching_sha2_password` (PyMySQL needs the `cryptography` package, which this toolkit installs). |
| Replication SQL | `SHOW MASTER STATUS`, `SHOW SLAVE STATUS` accepted | Syntax errors. Use `SHOW BINARY LOG STATUS`, `SHOW REPLICA STATUS`, `CHANGE REPLICATION SOURCE TO`. `mysql.rds_set_external_master*` procedures are replaced by `rds_set_external_source*` (verified by diffing `mysql.rds_%` routines). |
| FKs to non-unique keys | allowed | blocked (`restrict_fk_on_non_standard_key`) |
| `AUTO_INCREMENT` on `FLOAT`/`DOUBLE` | allowed | removed |
| Removed parameters | — | `expire_logs_days` (use `binlog_expire_logs_seconds`), `binlog_transaction_dependency_tracking` |
| InnoDB defaults | `innodb_io_capacity` 200, `innodb_log_buffer_size` 16 MB | 10000, 64 MB; `temptable_max_ram` and buffer-pool instances scale with instance size (AWS docs) |
| Privileges | `SET_USER_ID` | `SET_ANY_DEFINER`, `ALLOW_NONEXISTENT_DEFINER`, `FLUSH_PRIVILEGES`, `OPTIMIZE_LOCAL_TABLE` (AWS docs). Converted routines with a `DEFINER` need `SET_ANY_DEFINER` to create. |
| Histograms | `AUTO UPDATE` works | disabled from 8.4.7 (AWS docs) |
| Fast insert | available | not available |
| Removed objects | — | `INFORMATION_SCHEMA.TABLESPACES`; `LOCK TABLES … LOW_PRIORITY WRITE`; weak TLS ciphers (AWS docs) |
| Upgrade path | 2 → 3 in place | 3 → 8.4 in place; no direct 2 → 8.4 |

## AWS integrations on both versions (verified)

- Roles `AWS_LOAD_S3_ACCESS`, `AWS_SELECT_S3_ACCESS`, `AWS_LAMBDA_ACCESS`, `AWS_SAGEMAKER_ACCESS`,
  `AWS_COMPREHEND_ACCESS`, `AWS_BEDROCK_ACCESS` exist and are granted to `rds_superuser_role`.
- `LOAD DATA FROM S3`, `SELECT … INTO OUTFILE S3`, native `lambda_sync()`/`lambda_async()`, and
  `aws_comprehend_*` functions parse and run; each needs an IAM role associated with the cluster and set in
  `aws_default_s3_role` / `aurora_load_from_s3_role` / `aurora_select_into_s3_role` /
  `aws_default_lambda_role` / `aws_default_comprehend_role` (the verified errors name the missing parameter).
- The master user is **not** `SUPER`: it holds `rds_superuser_role`. `log_bin_trust_function_creators` = 0
  (verified); set it to 1 in the parameter group if binary logging is on and converted functions are not
  declared `DETERMINISTIC`/`NO SQL`/`READS SQL DATA`.
- Binary logging is off by default (`log_bin` = 0, verified); turn it on only for external
  replication or CDC (AWS DMS ongoing replication *from* Aurora).

## Tooling

- **AWS DMS** supports MySQL 8.0 **and 8.4** as data-migration targets, and Aurora MySQL and Aurora
  Serverless v2 targets ([DMS targets](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Introduction.Targets.html)).
- **AWS DMS Schema Conversion** lists **Aurora MySQL 8.0.32** (and RDS for MySQL 8.0.23) as its MySQL target
  data providers — not 8.4 (same page, checked 2026-10-29). Converting with DMS SC and applying to 8.4 works
  for most objects, but review FKs to non-unique keys, `AUTO_INCREMENT` on floating types and replication
  SQL for 8.4.
- **DMS homogeneous data migrations** list Aurora MySQL 5.7 and 8.0 targets only.
- **Aurora Serverless v1** reached end of life (2025-03-31); use Serverless v2 (min 0–256 ACU).
- **Performance Insights** reached end of life on 2026-07-31; use **CloudWatch Database Insights**.
- This toolkit loads data with PyMySQL batched `INSERT` (`./dbmig migrate-data`); for production volumes
  hand off to AWS DMS.
