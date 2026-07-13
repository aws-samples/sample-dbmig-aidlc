# Amazon Aurora Serverless v1 overview

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tools.auroraserverless.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A

## SQL Server
- Not applicable as a source. Aurora Serverless v1 is a **target deployment option** for the migrated database; SQL Server has no equivalent on-demand autoscaling configuration.

## PostgreSQL
- Aurora Serverless v1 is an on-demand autoscaling configuration available for **Aurora PostgreSQL-Compatible Edition** (and Aurora MySQL). A migrated Aurora PostgreSQL database can run as a Serverless v1 cluster.
- Cluster volume is **always encrypted** (you choose the key; encryption can't be disabled). Same encrypted-snapshot operations as provisioned clusters.

## Conversion notes
- **What it is:** An on-demand autoscaling configuration for Amazon Aurora that scales compute capacity up/down based on application needs (vs. provisioned clusters where you manage capacity manually). Auto starts up, scales, and shuts down when not in use.
- **Advantages:** Simpler than provisioned; scalable (no disruption to client connections); cost-effective (pay per-second for resources consumed); highly available storage (same fault-tolerant distributed storage with six-way replication as Aurora).
- **Use cases:** Infrequently used apps; new apps (unsure of instance size); variable workloads (HR, budgeting, operational reporting); unpredictable workloads (sudden activity surges); dev/test databases (auto shut down nights/weekends); multi-tenant applications (per-database capacity managed automatically).
- **Scaling behavior:**
  - Autoscaling thresholds: **1.5 minutes to scale up**, **5 minutes to scale down** (metrics must exceed/fall below limits for that duration to trigger).
  - Cool-down period between scaling activities: **5 minutes to scale up**, **15 minutes to scale down**.
  - Service must find a **"scaling point"** — may take longer with long-running transactions.
  - Scaling is transparent to clients/applications: existing connections and session state are transferred to new nodes.
  - Pausing/resuming adds higher latency only for the first connection (~25 seconds).
- **How to provision:** Management Console → Amazon RDS → Create database → Engine options → for Engine versions choose "Show versions that support Serverless v2" → choose capacity settings for your use case.
- **Pricing:** See Serverless Pricing under MySQL-Compatible or PostgreSQL-Compatible Edition on the Aurora pricing page.
