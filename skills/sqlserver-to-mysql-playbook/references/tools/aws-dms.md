# AWS Database Migration Service (AWS DMS) Overview

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.awsdms.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A — DMS handles data movement; SCT handles schema/code conversion. They are complementary.

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
