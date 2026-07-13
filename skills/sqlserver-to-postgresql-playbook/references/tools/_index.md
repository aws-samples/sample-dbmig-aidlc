# Tools & Services — Reference Index

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook — "Migration tools and services" chapter
> Base URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/

Reference files distilled from the playbook's migration tools & services pages. All entries
are **Conversion category: N/A (tooling)**.

| File | Topic | Summary |
|---|---|---|
| [aws-sct.md](aws-sct.md) | AWS Schema Conversion Tool | Java utility that connects source/target, assesses, and converts schema objects. Step-by-step project setup, assessment report, convert + apply/save-as-SQL. |
| [sct-action-code-index.md](sct-action-code-index.md) | SCT Action Code Index | Master index of SCT automation levels (5★→none) and all action codes per feature (tables, data types, cursors, triggers, indexes, partitioning, etc.). |
| [aws-dms.md](aws-dms.md) | AWS Database Migration Service | Managed data migration/replication. Full-load, full-load+CDC, CDC-only. Source/target support, HA failover, KMS/SSL/Secrets Manager security. |
| [rds-on-outposts.md](rds-on-outposts.md) | Amazon RDS on Outposts | Managed RDS on premises (SQL Server, MySQL, PostgreSQL). Not supported with Aurora. KMS-encrypted; backups to Region. |
| [rds-proxy.md](rds-proxy.md) | Amazon RDS Proxy | Managed connection-pooling proxy for Aurora/RDS PostgreSQL & MySQL. Cuts fail-over time up to 66% ([AWS RDS Proxy](https://aws.amazon.com/rds/proxy/)); Secrets Manager/IAM integration; no code changes. |
| [aurora-serverless-v1.md](aurora-serverless-v1.md) | Amazon Aurora Serverless v1 | On-demand autoscaling Aurora config for intermittent/unpredictable workloads. Scaling thresholds, encrypted storage, provisioning steps. |
| [native-tools.md](native-tools.md) | dbmig native-tools note | Informational: dbmig uses Python drivers (pytds for SQL Server, psycopg for PostgreSQL), not sqlcmd/bcp/psql. |

## Key takeaways
- **AWS SCT** converts schema/code objects; **AWS DMS** moves data. They are complementary.
- The **SCT Action Code Index** is the go-to map for what auto-converts vs. needs manual work.
- **RDS Proxy**, **RDS on Outposts**, and **Aurora Serverless v1** are target-side deployment/runtime options, not conversion tools.
- `dbmig` itself relies on Python drivers, independent of these AWS GUI/managed services (see native-tools.md).
