# Migration Tools and Services — Reference Index

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.html

Distilled reference notes for the AWS tools and services used to migrate Microsoft SQL Server 2019 to Amazon Aurora MySQL. These cover AWS SCT (schema conversion), AWS DMS (data movement), and several Aurora/RDS deployment and operational features. All are tooling-category references (no SQL conversion category).

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29). Target baseline: `../../../oracle-to-mysql-playbook/references/target-baseline-aurora-mysql.md` (shared by both MySQL playbooks). AWS DMS supports MySQL 8.4 targets; DMS Schema Conversion targets Aurora MySQL 8.0.32 only.

## Files

| File | Topic | Category |
|---|---|---|
| [aws-sct.md](aws-sct.md) | AWS Schema Conversion Tool overview — install, configure, project workflow | Tooling (schema conversion) |
| [action-code.md](action-code.md) | AWS SCT action code index + verified table of codes obsolete on Aurora MySQL 3 / 8.4 | Tooling (conversion reference) |
| [aws-dms.md](aws-dms.md) | AWS Database Migration Service overview — data movement, how it works | Tooling (data migration) |
| [rds-outposts.md](rds-outposts.md) | Amazon RDS on Outposts overview (RDS only, not Aurora) | Tooling (deployment) |
| [rds-proxy.md](rds-proxy.md) | Amazon RDS Proxy overview — connection pooling, failover, security | Tooling (connection management) |
| [aurora-serverless.md](aurora-serverless.md) | Amazon Aurora Serverless **v2** (v1 reached end of life 2025-03-31) | Tooling (deployment) |
| [aurora-backtrack.md](aurora-backtrack.md) | Amazon Aurora Backtrack overview — rewind cluster in place | Tooling (operations) |
| [parallel-query.md](parallel-query.md) | Amazon Aurora Parallel Query overview — storage-layer analytical queries | Tooling (performance) |
| [native-tools.md](native-tools.md) | How dbmig connects (Python drivers) vs. native client tools — informational | Informational |

## Two complementary AWS migration tools
- **AWS SCT** — converts schema and code objects (tables, views, indexes, procedures, triggers). Auto-converts compatible objects; flags the rest with action codes (see action-code.md).
- **AWS DMS** — moves the data (full load + optional ongoing CDC) while the source stays operational. Can create target tables/PKs or rely on SCT-created schema.

## Aurora MySQL target features referenced
- **RDS Proxy** — connection pooling, up to 66% faster failover ([AWS RDS Proxy](https://aws.amazon.com/rds/proxy/)), Secrets Manager/IAM auth.
- **Aurora Serverless v2** — on-demand autoscaling capacity in ACUs (v1 is retired).
- **Aurora Backtrack** — rewind the cluster in minutes (Aurora MySQL 2, 3 and 8.4; 72 h window).
- **Aurora Parallel Query** — storage-layer push-down for analytics; off by default; not with I/O-Optimized.
- **RDS on Outposts** — RDS (not Aurora) on-premises hybrid deployment.
