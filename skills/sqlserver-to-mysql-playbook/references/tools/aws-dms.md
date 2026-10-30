# AWS Database Migration Service (AWS DMS) Overview

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.awsdms.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A — DMS handles data movement; SCT handles schema/code conversion. They are complementary.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): DMS supports MySQL 8.0/8.4 targets, DMS SC only Aurora MySQL 8.0.32 (AWS docs); SQL Server CDC prerequisites, load pattern, data-type traps, 8.4 auth/TLS (verified).

## SQL Server
SQL Server is a supported AWS DMS source engine. DMS migrates data while the source database remains fully operational, minimizing application downtime. Supports homogeneous (e.g., Oracle→Oracle) and heterogeneous (e.g., SQL Server→MySQL) migrations. Supports continuous data replication with high availability (CDC).

## MySQL
Aurora MySQL / MySQL is a supported AWS DMS target engine. DMS can create tables and associated primary keys on the target if they don't exist, or you can pre-create target tables manually — or use AWS SCT to create target tables, indexes, views, triggers, etc.

## Conversion notes
- **What DMS does:** Fully managed deployment, management, and monitoring of all hardware/software for migration. Start within minutes of configuring.
- **Scalable:** Scale migration resources up/down to match workload (e.g., increase allocated storage and restart, usually within minutes).
- **Pricing:** Pay-as-you-go; pay only while using resources (no up-front licensing). See Database Migration Service pricing.
- **Managed infrastructure:** Handles hardware, software, patching, and error reporting automatically.
- **Automatic failover:** If the primary replication server fails, a backup replication server takes over with little/no service interruption.
- **Engine flexibility:** Switch engines (e.g., to Amazon RDS/Aurora, Redshift, DynamoDB, S3) or keep the same engine on new infra.
- **Supported sources:** Oracle, Microsoft SQL Server, MySQL, MariaDB, PostgreSQL, Db2 LUW, SAP ASE, MongoDB, Amazon Aurora.
- **Supported targets:** Oracle, Microsoft SQL Server, PostgreSQL, MySQL, Amazon Redshift, SAP ASE, Amazon S3, Amazon DynamoDB. Fully heterogeneous source→target migrations supported.
- **Security:** Data at rest encrypted with AWS KMS; in-flight data can use SSL.
- **How it works:** DMS is a server in the AWS Cloud running replication software. You create source and target connections, then schedule a task that moves data. DMS creates tables and primary keys on the target if absent.
- **References:** "What is Database Migration Service?" and "Best practices for Database Migration Service" in the AWS DMS User Guide.

### Aurora MySQL 8.4 / 3 target notes
- DMS lists MySQL **8.0 and 8.4** (and Aurora MySQL, Aurora Serverless v2) as data-migration targets; **DMS Schema Conversion** lists only **Aurora MySQL 8.0.32** as its Aurora MySQL target data provider ([DMS targets](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Introduction.Targets.html), checked 2026-10-29). For an 8.4 target, convert against 8.0 and fix 8.4 breaks (FKs to non-unique keys, `AUTO_INCREMENT` on `FLOAT`/`DOUBLE`). See `../../../oracle-to-mysql-playbook/references/target-baseline-aurora-mysql.md`.
- SQL Server CDC as a DMS source needs MS-CDC or MS-Replication enabled on the source tables (and the `distribution` database for replication-based capture).
- Pre-create the schema (toolkit `apply-schema` or SCT/DMS SC), run full load with `TargetTablePrepMode=DO_NOTHING`, then add secondary indexes, FKs and triggers. DMS does not migrate T-SQL code.
- Data-type traps to check in DMS table mappings: `DATETIMEOFFSET` (offset is lost), `UNIQUEIDENTIFIER` → `CHAR(36)`/`BINARY(16)`, `NVARCHAR(MAX)` → `LONGTEXT`, `HIERARCHYID`/`SQL_VARIANT` (unsupported).
- The DMS target user must authenticate with `caching_sha2_password` on 8.4 (the default `authentication_policy`) and connect over TLS (8.4 requires it by default, verified).
