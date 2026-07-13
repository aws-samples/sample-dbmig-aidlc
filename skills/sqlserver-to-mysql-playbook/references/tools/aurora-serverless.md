# Amazon Aurora Serverless v1 Overview

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.auroraserverless.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A — target deployment/capacity option.

## SQL Server
N/A on the source side. Presented as a target deployment model to consider when migrating off SQL Server.

## MySQL
Amazon Aurora Serverless is an on-demand, autoscaling configuration for Amazon Aurora (MySQL-compatible and PostgreSQL-compatible). The Aurora MySQL target can be deployed as Serverless v1 or v2 instead of a provisioned cluster.

## Conversion notes
### Aurora Serverless v1
- **On-demand autoscaling:** Scales compute capacity up/down based on application needs; automatically starts, scales, and shuts down when not in use.
- **Best for:** Infrequent, intermittent, or unpredictable workloads.
- **Advantages:** Simpler than provisioned; scalable with no disruption to client connections; cost-effective (per-second billing for consumed resources); highly available storage (six-way replication, fault-tolerant distributed storage).
- **Encryption:** The cluster volume is always encrypted; you can choose the key but can't turn encryption off.
- **Use cases:** Infrequently used apps (e.g., low-volume blog); new apps with unknown sizing; variable workloads (HR, budgeting, operational reporting); unpredictable workloads with sudden spikes; dev/test databases (auto shutdown nights/weekends); multi-tenant applications.
- **Scaling behavior:** Storage shared between nodes; can scale up/down in seconds for most workloads. Autoscaling thresholds: ~1.5 min to scale up, ~5 min to scale down (metrics must stay over/under limits for those durations). Cooldown: 5 min after scale-up, 15 min after scale-down. Service must find a "scaling point" (long-running transactions delay this). Scaling is transparent — existing connections and session state transfer to new nodes. Pausing/resuming adds higher first-connection latency (~25 seconds).

### Aurora Serverless v2
- Architected from the ground up for instantly scalable serverless clusters with security/isolation for multitenant environments; low overhead, fast response, scales to large processing demand.
- **Capacity range:** Defined as min/max **Aurora Capacity Units (ACUs)**. Each ACU = 2 GiB RAM + associated vCPU + networking.
- **Scaling:** Unlike v1 (which doubles ACUs at thresholds), v2 increases ACUs **incrementally** in the precise increments needed for best performance per resources consumed.

### How to provision (v2)
- AWS Management Console → **Amazon RDS** → **Create database** → under **Engine options / Engine versions**, choose **Show versions that support Serverless v2** → choose capacity settings for your use case.
