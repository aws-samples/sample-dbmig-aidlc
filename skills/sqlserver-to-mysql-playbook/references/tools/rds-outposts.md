# Amazon RDS on Outposts Overview

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.rdsoutposts.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A
**Note:** This topic is related to Amazon RDS and is **not** supported with Amazon Aurora.

## SQL Server
Amazon RDS on Outposts supports the Microsoft SQL Server database engine on-premises, providing a consistent hybrid experience for workloads that must run close to on-premises data and applications.

## MySQL
Amazon RDS on Outposts supports the MySQL (and PostgreSQL) engines, with additional engines coming. Note: this is RDS for MySQL on Outposts, not Aurora MySQL — Aurora is not supported on Outposts.

## Conversion notes
- **What it is:** Fully managed service that extends the same AWS infrastructure, services, APIs, and tools to virtually any data center, co-location space, or on-premises facility.
- **Use cases:** Workloads requiring low-latency access to on-premises systems, local data processing, data residency, and migration of applications with local system inter-dependencies.
- **How it works:** Deploy and scale an RDS DB instance in Outposts just as in the cloud, using the AWS Console, APIs, or CLI.
- **Encryption:** RDS databases in Outposts are encrypted at rest using AWS KMS keys.
- **Backups:** Automatic backups and manual snapshots are stored in the parent AWS Region; supports automatic backup to a Region.
- **Management:** Manage both cloud and on-premises RDS databases with the same Console, APIs, and CLI.
- **Supported engines:** Microsoft SQL Server, MySQL, PostgreSQL (more coming).
