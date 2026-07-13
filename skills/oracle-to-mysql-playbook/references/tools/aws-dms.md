# AWS Database Migration Service (AWS DMS)

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tools.awsdms.html

**Conversion category:** N/A (data migration service)
**SCT automation:** N/A — DMS handles data movement; AWS SCT handles schema/object conversion. DMS can create target tables and primary keys automatically if absent, or you can pre-create them (manually or via AWS SCT).

## Overview

AWS DMS helps you migrate databases to AWS quickly and securely. The source database remains fully operational during migration, minimizing application downtime. DMS can migrate data to and from most widely-used commercial and open-source databases.

It supports:
- **Homogeneous migrations** (e.g., Oracle → Amazon RDS for Oracle).
- **Heterogeneous migrations** between different platforms (e.g., Oracle → Amazon Aurora MySQL).
- Streaming data to Amazon Redshift, Amazon DynamoDB, and Amazon S3 from any supported source.
- Continuous data replication with high availability.

Supported sources include: Amazon Aurora, PostgreSQL, MySQL, MariaDB, Oracle Database, SAP ASE, SQL Server, IBM Db2 LUW, and MongoDB.
Supported targets include: Oracle, Microsoft SQL Server, PostgreSQL, MySQL, Amazon Redshift, SAP ASE, Amazon S3, and Amazon DynamoDB.

Pricing: see Database Migration Service pricing (https://aws.amazon.com/dms/pricing).

## Migration tasks performed by AWS DMS

- Automatically manages deployment, management, and monitoring of all hardware and software needed for the migration — you can start within minutes.
- Scale migration resources up or down to match the actual workload (e.g., increase allocated storage and restart, usually within minutes).
- Pay-as-you-go model — pay only for resources while in use, no up-front license or ongoing maintenance charges.
- Automatically manages supporting infrastructure: hardware, software, software patching, and error reporting.
- Provides automatic failover — if the primary replication server fails, a backup replication server takes over with little or no interruption.
- Helps switch to a more cost-effective engine (e.g., Amazon RDS, Aurora, Redshift, DynamoDB, S3) or keep the same engine while moving off old infrastructure.
- Security: data at rest is encrypted with AWS KMS; in-flight data can be encrypted with SSL.

## How AWS DMS works

At its most basic, AWS DMS is a server in the AWS Cloud running replication software:

1. You create a **source** and a **target** connection to tell DMS where to extract from and load to.
2. You schedule a **task** that runs on this server to move your data.
3. DMS creates the tables and associated primary keys if they don't exist on the target. You can pre-create target tables manually, or use AWS SCT to create some or all target tables, indexes, views, triggers, and so on.

See "What is Database Migration Service?" and "Best practices for Database Migration Service" in the DMS User Guide.

## Conversion notes

- DMS moves **data**; it does not convert schema/PL-SQL logic — pair it with AWS SCT for heterogeneous Oracle→Aurora MySQL migrations.
- DMS can auto-create target tables + primary keys, but for full fidelity (indexes, views, triggers) pre-create the schema with AWS SCT.
- Source stays online during migration, enabling near-zero-downtime cutover via continuous replication (CDC).
- Use SSL for in-flight encryption and KMS for at-rest encryption.
- Automatic failover (backup replication server) provides resilience during long migrations.
