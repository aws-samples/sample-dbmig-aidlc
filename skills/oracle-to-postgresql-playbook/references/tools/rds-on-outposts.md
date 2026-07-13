# Amazon RDS on Outposts

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tools.rdsoutposts.html

**Conversion category:** N/A (deployment/infrastructure option)
**SCT automation:** N/A

> Note: This topic relates to **Amazon RDS** only and is **not supported with Amazon Aurora**.

## Oracle
Not an Oracle feature. Provided as an AWS deployment option for hybrid/on-premises scenarios when migrating off Oracle.

## PostgreSQL
Amazon RDS on Outposts is a fully managed service that brings the same AWS infrastructure, services, APIs, and tools to virtually any data center, co-location space, or on-premises facility for a consistent hybrid experience. It is ideal for workloads needing:
- Low-latency access to on-premises systems
- Local data processing
- Data residency
- Migration of applications with local system inter-dependencies

**How it works:** You deploy and scale an RDS DB instance on Outposts (on premises / co-location) just as in the cloud, using the AWS Management Console, APIs, or CLI. Databases on Outposts are encrypted at rest using AWS KMS keys. RDS automatically stores all automatic backups and manual snapshots in the parent AWS Region. Supported engines: **Microsoft SQL Server, MySQL, and PostgreSQL** (more coming).

## Conversion notes
- **Aurora is not supported on Outposts** — for an Oracle→Aurora PostgreSQL target, Outposts does not apply. Use it only if the target is RDS for PostgreSQL.
- Use case: run RDS on premises for low-latency workloads that must sit close to on-premises data/applications, while still getting managed backups to an AWS Region.
- Same management plane (console/API/CLI) for cloud and on-premises instances.
- See: AWS Outposts Family, Amazon RDS on Outposts, and "Create Amazon RDS DB Instances on AWS Outposts."
