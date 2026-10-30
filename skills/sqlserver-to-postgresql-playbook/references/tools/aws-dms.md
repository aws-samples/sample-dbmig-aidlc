# AWS Database Migration Service (AWS DMS) overview

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tools.awsdms.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A. DMS migrates **data** (and optionally creates target tables/PKs); schema/code object conversion is handled by AWS SCT.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): DMS 3.5.4+ for PG 17/18 targets (AWS docs), SQL Server CDC prerequisites, PG 18 target checklist.

## SQL Server
- SQL Server is a supported **source** for DMS. The source database remains fully operational during migration, minimizing application downtime.
- Supports homogeneous (e.g. Oracle→Oracle) and heterogeneous (e.g. SQL Server→MySQL/PostgreSQL) migrations.
- Supported sources include: Amazon Aurora, PostgreSQL, MySQL, MariaDB, Oracle, SAP ASE, SQL Server, IBM DB2 LUW, and MongoDB.
- TLS 1.2 supported for SQL Server endpoints.

## PostgreSQL
- Aurora PostgreSQL is a supported **target**. DMS creates tables and associated primary keys on the target if they don't exist; you can pre-create target tables manually, or use AWS SCT to create tables/indexes/views/triggers/etc.
- Supported targets include: Oracle, SQL Server, PostgreSQL, MySQL, Amazon Redshift, SAP ASE, Amazon S3, and Amazon DynamoDB.
- Can also stream data to Redshift, DynamoDB, and S3 from any supported source.

## Conversion notes
- **How it works:** DMS is a server in the AWS Cloud running replication software. You create source + target endpoint connections, then schedule a task that moves data. Supports full-load, full-load + CDC (change data capture), and CDC-only tasks.
- **Managed infrastructure:** DMS auto-manages deployment, hardware/software, patching, and error reporting. Supports scaling up/down (e.g. increase storage and restart). Pay-as-you-go pricing.
- **High availability:** Automatic failover — if the primary replication server fails, a backup replication server takes over with little/no interruption.
- **Security:** Data at rest encrypted with AWS KMS; in-flight data can be encrypted with SSL. Supports AWS Secrets Manager integration — store DB connection credentials as secrets instead of plaintext, then submit the secret when creating/modifying an endpoint.
- **Latest updates noted:** full-load+CDC and CDC-only tasks for Oracle source tables created with `CREATE TABLE AS`; MySQL 8.0 as source (except compressed transaction payload); Oracle extended data types (source + target); TLS 1.2 for MySQL and SQL Server endpoints.
- For a step-by-step SQL Server → Aurora walkthrough, see the DMS Step-by-Step guide; also see "What is Database Migration Service?" and "Best practices for Database Migration Service."

### Aurora PostgreSQL 18 notes
- AWS DMS supports PostgreSQL 17.x and 18.x **targets only from replication engine 3.5.4** ([DMS targets](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Introduction.Targets.html)). Pin the replication instance or DMS Serverless config accordingly.
- SQL Server CDC source prerequisites: MS-CDC or MS-Replication enabled on the source tables, `FULL` recovery model, and log retention long enough for the task.
- Target checklist: exclude **generated columns** (PG 18 `VIRTUAL`/`STORED`, converted from computed columns) from table mappings; keep identity columns `BY DEFAULT` during load or rely on `OVERRIDING SYSTEM VALUE`; create FKs and triggers after full load; reset identities at cutover (`./dbmig reset-identity`); validate `datetime` precision and `money` → `numeric(19,4)`.
- DMS Serverless and DMS Schema Conversion remove replication-instance sizing and desktop SCT for most projects.
