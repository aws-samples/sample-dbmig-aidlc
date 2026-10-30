# Special Features — Oracle → Aurora MySQL Reference Index

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> Base URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/

Distilled reference pages for Oracle "special features" and their Aurora MySQL equivalents. Each file follows the same structure (topic, conversion category, SCT automation, Oracle usage, MySQL usage, conversion notes) and preserves source SQL/code examples.

Conversion categories used here: **Automatic** (high compatibility, minimal/automatic change), **Assisted** (partial automation; rewrite needed), **Manual** (no automation; re-architect), **Blocked** (no equivalent).

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29). Baseline: `../target-baseline-aurora-mysql.md`.

| Reference file | Topic | Conversion category | Aurora MySQL equivalent |
|---|---|---|---|
| [advanced-queuing-and-lambda.md](advanced-queuing-and-lambda.md) | Oracle Advanced Queuing (AQ) | Manual | No AQ; native `lambda_async()`/`lambda_sync()` (the `mysql.lambda_async` procedure is gone) + SQS/SNS, or a `SKIP LOCKED` queue table. |
| [character-sets.md](character-sets.md) | Character sets & collations | Automatic | Default `utf8mb4`/`utf8mb4_0900_ai_ci` (accent- and case-insensitive); MySQL `NCHAR`/`NVARCHAR` mean `utf8mb3` — map national types to `utf8mb4` `VARCHAR`. |
| [database-links-and-fqtn.md](database-links-and-fqtn.md) | Database links | Manual | No DB links; `db.table` within one cluster; `FEDERATED` unavailable and silently replaced by InnoDB. |
| [dbms-scheduler-and-events.md](dbms-scheduler-and-events.md) | DBMS_SCHEDULER jobs | Manual | `CREATE EVENT` (scheduler ON by default on Aurora); EventBridge Scheduler or `lambda_async()` for external jobs; job log table. |
| [external-tables-and-s3.md](external-tables-and-s3.md) | External tables | Manual | No live external tables; `LOAD DATA FROM S3` / `SELECT INTO OUTFILE S3` (CSV); Athena/Redshift Spectrum to query in place. |
| [inline-views.md](inline-views.md) | Inline views / subqueries | Automatic | Derived tables need an alias (error 1248); `JOIN LATERAL` for correlated inline views. |
| [json-support.md](json-support.md) | JSON documents | Assisted | Native `JSON` + `JSON_TABLE`/`JSON_VALUE`; generated-column, functional and multi-valued indexes; `JSON_SCHEMA_VALID` checks. |
| [materialized-views-and-summary-tables.md](materialized-views-and-summary-tables.md) | Materialized views | Manual | No MVs: summary tables refreshed by events (atomic `RENAME`) or triggers; zero-ETL to Redshift for heavy reporting. |
| [multitenant-and-databases.md](multitenant-and-databases.md) | Multitenant CDB/PDB | Manual | PDB → database in a cluster or a separate cluster; fast cloning / blue-green for PDB clone/refresh. |
| [resource-manager-and-dedicated-clusters.md](resource-manager-and-dedicated-clusters.md) | Resource Manager | Manual | No resource manager (resource groups need a privilege Aurora withholds); dedicated clusters/readers, per-account limits, `max_execution_time`. |
| [securefile-lobs-and-large-objects.md](securefile-lobs-and-large-objects.md) | SecureFile LOBs | Assisted | `CLOB`/`BLOB` → `LONGTEXT`/`LONGBLOB`; prefix indexes only; NO PAD trailing-space semantics; S3 for large files. |
| [synonyms.md](synonyms.md) | Synonyms | Manual | No synonyms; updatable views, wrapper routines, or fully-qualified names. |
| [table-compression.md](table-compression.md) | Table compression | Manual | No compressed tables: `ROW_FORMAT=COMPRESSED` silently becomes `COMPACT`; page compression fails. |
| [views.md](views.md) | Views | Automatic | Views convert directly; no `FORCE`, no `WITH READ ONLY`; join views update one base table; no `INSTEAD OF` triggers. |
| [xml-db-and-xml.md](xml-db-and-xml.md) | XML DB / XMLType | Assisted | No XML type; `ExtractValue`/`UpdateXML` (namespaces ignored, NULL on malformed XML); prefer JSON. |
| [log-miner-and-logs.md](log-miner-and-logs.md) | Log Miner | Manual | Binary log + `mysqlbinlog` replace Log Miner; binlog off by default; `log_output` = FILE; CloudWatch export. |
| [sql-result-cache-and-query-cache.md](sql-result-cache-and-query-cache.md) | SQL Result Cache | Manual | No result/query cache; `SQL_CACHE` is a syntax error on 3 / 8.4 — remove it. |

## Quick guidance

- **Automatic / largely direct:** character sets, inline views, views.
- **Assisted (rewrite, feature partially present):** JSON, LOBs, XML.
- **Manual / re-architect (no in-database equivalent):** advanced queuing, database links, scheduler, external tables, materialized views, multitenant, resource manager, synonyms, table compression, log miner, result cache.
- Several Oracle features map to **AWS services** rather than database features: AQ → Lambda/SQS/SNS; external tables → S3 integration + Athena; resource manager → dedicated clusters; log miner → binlog/CloudWatch; materialized views for reporting → zero-ETL to Redshift.
- Several DDL options are **silently ignored** on Aurora MySQL instead of failing: `ENGINE=FEDERATED` (becomes InnoDB), `ROW_FORMAT=COMPRESSED` (becomes COMPACT). Check `information_schema.tables` after applying converted DDL.
