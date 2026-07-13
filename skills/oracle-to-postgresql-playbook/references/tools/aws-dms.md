# AWS Database Migration Service (AWS DMS)

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tools.awsdms.html

**Conversion category:** N/A (migration/data-replication service page)
**SCT automation:** N/A. DMS handles data migration; AWS SCT handles schema/object conversion. DMS can create target tables and primary keys if they don't exist, or you can pre-create them (manually or via SCT).

## Oracle
AWS DMS migrates databases to AWS quickly and securely while the source database remains fully operational, minimizing downtime. Supported as a source for this playbook is Oracle.

Supported sources (broad): Amazon Aurora, PostgreSQL, MySQL, MariaDB, Oracle Database, SAP ASE, SQL Server, IBM Db2 LUW, and MongoDB.

DMS supports both **homogeneous** migrations (e.g., Oracle → Oracle) and **heterogeneous** migrations between different platforms (e.g., Oracle → Amazon Aurora). It also supports **continuous data replication** with high availability (CDC).

## PostgreSQL
DMS can target Aurora PostgreSQL (and other engines). Supported targets: Oracle, Microsoft SQL Server, PostgreSQL, MySQL, Amazon Redshift, SAP ASE, Amazon S3, and Amazon DynamoDB. You can migrate from any supported source to any supported target (fully heterogeneous).

**How DMS works:** DMS is a server in the AWS Cloud running replication software. You create a **source** and **target** connection (endpoints) telling DMS where to extract from and load to, then schedule a **task** that moves the data. DMS creates target tables and associated primary keys if they don't already exist; you may pre-create target tables manually, or use AWS SCT to create some/all target tables, indexes, views, triggers, etc.

## Conversion notes
- **Division of labor:** AWS SCT converts schema and code objects; AWS DMS moves the data. Use them together for heterogeneous Oracle→Aurora PostgreSQL migrations.
- **Managed infrastructure:** DMS automatically manages deployment, hardware/software, patching, monitoring, and error reporting. You can scale replication storage/compute up or down and restart, usually within minutes.
- **Pay-as-you-go:** Pay only for DMS resources while in use; no up-front licensing.
- **High availability:** Automatic failover — a backup replication server takes over with little/no interruption if the primary fails.
- **Security:** Data at rest encrypted with AWS KMS; in-flight data can be encrypted with SSL. Endpoint credentials can be stored in AWS Secrets Manager and referenced instead of plaintext.
- **CDC / latest updates noted:** full-load + CDC and CDC-only tasks against Oracle source tables created via `CREATE TABLE AS`; MySQL 8.0 source support (except compressed transaction payloads); AWS Secrets Manager integration for endpoints; TLS 1.2 for MySQL and SQL Server endpoints.
- See "What is Database Migration Service" and "Best practices for Database Migration Service" in the DMS user guide for deeper guidance.
