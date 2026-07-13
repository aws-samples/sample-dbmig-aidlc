# Special Features — Oracle → Aurora MySQL Reference Index

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> Base URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/

Distilled reference pages for Oracle "special features" and their Aurora MySQL equivalents. Each file follows the same structure (topic, conversion category, SCT automation, Oracle usage, MySQL usage, conversion notes) and preserves source SQL/code examples.

Conversion categories used here: **Automatic** (high compatibility, minimal/automatic change), **Assisted** (partial automation; rewrite needed), **Manual** (no automation; re-architect), **Blocked** (no equivalent).

| Reference file | Topic | Conversion category | Aurora MySQL equivalent |
|---|---|---|---|
| [advanced-queuing-and-lambda.md](advanced-queuing-and-lambda.md) | Oracle Advanced Queuing (AQ) | Manual | AWS Lambda + Amazon SQS/SNS (`mysql.lambda_async`) |
| [character-sets.md](character-sets.md) | Character sets & collations | Automatic | Per-column charset/collation; `ALTER DATABASE` |
| [database-links-and-fqtn.md](database-links-and-fqtn.md) | Database links | Manual | Fully-qualified `db.table` (same cluster only); no remote links |
| [dbms-scheduler-and-events.md](dbms-scheduler-and-events.md) | DBMS_SCHEDULER jobs | Manual | `CREATE EVENT`, Lambda for executables, triggers/control tables for chains |
| [external-tables-and-s3.md](external-tables-and-s3.md) | External tables | Manual | S3 integration: `SELECT INTO OUTFILE S3`, `LOAD DATA/XML FROM S3` |
| [inline-views.md](inline-views.md) | Inline views / subqueries | Automatic | Same, but derived tables require a mandatory alias |
| [json-support.md](json-support.md) | JSON documents | Assisted | Native `JSON` type + 25+ functions; index via generated columns |
| [materialized-views-and-summary-tables.md](materialized-views-and-summary-tables.md) | Materialized views | Manual | Summary tables (triggers/events) or plain views + Parallel Query |
| [multitenant-and-databases.md](multitenant-and-databases.md) | Multitenant CDB/PDB | Manual | Multiple databases per Aurora cluster and/or separate clusters |
| [resource-manager-and-dedicated-clusters.md](resource-manager-and-dedicated-clusters.md) | Resource Manager | Manual | Dedicated Aurora clusters/replicas; `max_execution_time`; processlist |
| [securefile-lobs-and-large-objects.md](securefile-lobs-and-large-objects.md) | SecureFile LOBs | Assisted | `BLOB`/`TEXT` families (no SecureFile compression/dedup/TDE) |
| [synonyms.md](synonyms.md) | Synonyms | Manual | Encapsulating views / wrapper procedures/functions (no direct equivalent) |
| [table-compression.md](table-compression.md) | Table compression | Manual | Not supported (`ROW_FORMAT` non-compressed); no partition compression |
| [views.md](views.md) | Views | Automatic | `CREATE VIEW` with `ALGORITHM`/`DEFINER`/`SQL SECURITY`; updatable views |
| [xml-db-and-xml.md](xml-db-and-xml.md) | XML DB / XMLType | Assisted | Minimal XML (`ExtractValue`, `UpdateXML`); prefer native JSON |
| [log-miner-and-logs.md](log-miner-and-logs.md) | Log Miner | Manual | `mysqlbinlog` + binlog; error/general/slow logs; CloudWatch Logs |
| [sql-result-cache-and-query-cache.md](sql-result-cache-and-query-cache.md) | SQL Result Cache | Manual | Query Cache deprecated/removed — do not use; use indexing/ElastiCache |

## Quick guidance

- **Automatic / largely direct:** character sets, inline views, views.
- **Assisted (rewrite, feature partially present):** JSON, LOBs, XML.
- **Manual / re-architect (no in-database equivalent):** advanced queuing, database links, scheduler, external tables, materialized views, multitenant, resource manager, synonyms, table compression, log miner, result cache.
- Several Oracle features map to **AWS services** rather than database features: AQ → Lambda/SQS/SNS; external tables → S3 integration; resource manager → dedicated clusters; log miner → binlog/CloudWatch.
