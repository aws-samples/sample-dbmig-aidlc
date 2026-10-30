# Special Features — Oracle → Aurora PostgreSQL Reference Index

Distilled from the AWS *Oracle to Aurora PostgreSQL Migration Playbook* (Special features chapter). Each file documents the Oracle behavior, the PostgreSQL/Aurora equivalent, and conversion notes with preserved SQL examples.

| File | Summary |
|---|---|
| [character-sets-and-encoding.md](character-sets-and-encoding.md) | Oracle character sets (VARCHAR2/NVARCHAR2, AL32UTF8/AL16UTF16) vs PostgreSQL encodings + locale; no NCHAR/UTF-16; changing encoding requires export/recreate/import. (Assisted) |
| [database-links-dblink-fdw.md](database-links-dblink-fdw.md) | Oracle DATABASE LINK vs PostgreSQL `dblink` and `postgres_fdw`; FDW server = permanent named link; `oracle_fdw`/`tds_fdw`/`mysql_fdw` available on Aurora 18; credential caveats. (Manual) |
| [dbms-scheduler-and-lambda.md](dbms-scheduler-and-lambda.md) | Oracle DBMS_SCHEDULER (time/event/chained jobs) vs `pg_cron` (in-database, verified on 18) and EventBridge Scheduler + Lambda/Step Functions (external/chains). (Manual) |
| [external-tables-and-s3.md](external-tables-and-s3.md) | Oracle external tables (ORACLE_LOADER/DATAPUMP/HDFS/HIVE) vs Aurora `aws_s3` export/import functions; no external tables in PostgreSQL. (Manual) |
| [inline-views.md](inline-views.md) | Inline views/subqueries — fully compatible; FROM-subquery alias optional since PG 16 (still recommended). (Automatic) |
| [json-support.md](json-support.md) | Oracle JSON (CLOB + IS JSON, dot notation) vs PostgreSQL JSONB; PG 17/18 SQL/JSON (`JSON_VALUE`/`JSON_QUERY`/`JSON_TABLE`/`IS JSON`) convert near-directly; dot notation must be rewritten. (Assisted) |
| [materialized-views.md](materialized-views.md) | Oracle MViews (fast/complete refresh, MV logs, ON COMMIT) vs PostgreSQL complete-only refresh (`CONCURRENTLY` with a unique index), `pg_cron`-scheduled refresh, no DML. (Assisted) |
| [multitenant-architecture.md](multitenant-architecture.md) | Oracle CDB/PDB multitenant vs Aurora cluster + multiple databases / separate clusters; TEMPLATE cloning, logical replication. (Assisted) |
| [resource-manager-and-dedicated-clusters.md](resource-manager-and-dedicated-clusters.md) | Oracle Resource Manager (consumer groups/plans/directives) vs dedicated/right-sized Aurora clusters, custom endpoints, and per-role timeouts (`statement_timeout`, `transaction_timeout`, `idle_session_timeout`). (Manual/architectural) |
| [securefile-lobs-and-large-objects.md](securefile-lobs-and-large-objects.md) | Oracle SecureFile LOBs (compression/dedup/encryption) vs PostgreSQL BYTEA/TEXT (1 GB each) + TOAST (`lz4` per column) + KMS; SecureFiles unsupported. (Assisted) |
| [views.md](views.md) | Oracle views (simple/complex, CHECK OPTION, INSTEAD OF) vs PostgreSQL auto-updatable simple views and CASCADED/LOCAL CHECK OPTION. **Views are converted in the stored-code pass and load after functions (views call functions).** Top failure is Oracle's implicit numeric↔varchar coercion, which PostgreSQL rejects — add explicit casts and treat it as a data-quality finding. `CREATE FORCE VIEW` hides broken references in the source, so conversion surfaces pre-existing rot. (Assisted) |
| [xml-db-and-xml-type.md](xml-db-and-xml-type.md) | Oracle XML DB (XMLType, XMLIndex, XQuery, SQL/XML functions) vs PostgreSQL xml type, xpath()/xmltable(); no XQuery or XSD validation. (Assisted) |
| [log-miner-and-logging.md](log-miner-and-logging.md) | Oracle Log Miner (redo logs, SQL_REDO/SQL_UNDO) vs PostgreSQL pg_stat_statements, statement logging/pgaudit, logical decoding, CloudWatch Database Insights; no SQL_UNDO. (Manual) |
