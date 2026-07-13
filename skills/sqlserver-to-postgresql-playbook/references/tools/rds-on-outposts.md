# Amazon RDS on Outposts overview

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tools.rdsoutposts.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A

> **Note:** This topic relates to Amazon RDS and is **not supported with Amazon Aurora**.

## SQL Server
- RDS on Outposts supports **Microsoft SQL Server** as a database engine (alongside MySQL and PostgreSQL), letting you run a fully managed SQL Server instance on premises.

## PostgreSQL
- RDS on Outposts supports the **PostgreSQL** engine on premises (note: Aurora PostgreSQL itself is not supported on Outposts — this is RDS for PostgreSQL).

## Conversion notes
- **What it is:** A fully managed service that extends the same AWS infrastructure, services, APIs, and tools to virtually any data center, co-location space, or on-premises facility for a consistent hybrid experience.
- **Use cases:** Workloads needing low-latency access to on-premises systems, local data processing, data residency, and migration of applications with local system inter-dependencies.
- **How it works:** Deploy and scale RDS DB instances in Outposts just as in the cloud, via the AWS Console, APIs, or CLI. Databases are **encrypted at rest using AWS KMS keys**.
- **Backups:** Automatic backups and manual snapshots are stored in the AWS Region (automatic backup to Region).
- Supported engines: Microsoft SQL Server, MySQL, PostgreSQL (more coming).
- See: AWS Outposts Family, Amazon RDS on Outposts, and "Create Amazon RDS DB Instances on Outposts."
