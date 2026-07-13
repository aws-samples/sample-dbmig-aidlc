# Amazon Aurora Serverless v1

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tools.auroraserverless.html

**Conversion category:** N/A (target deployment/capacity option)
**SCT automation:** N/A

## Oracle
Not an Oracle feature. Conceptually relevant when sizing the target: instead of manually provisioning fixed capacity (as with a traditional Oracle instance), the target Aurora cluster can autoscale on demand.

## PostgreSQL
Amazon Aurora Serverless v1 is an on-demand, autoscaling configuration for Amazon Aurora (PostgreSQL-compatible and MySQL-compatible editions). The DB cluster scales compute capacity up and down based on application needs, in contrast to provisioned clusters where you manage capacity manually. It automatically starts up, scales to match usage, and shuts down when not in use — cost-effective for infrequent, intermittent, or unpredictable workloads.

The cluster volume uses the same high-capacity, distributed, highly available storage as provisioned clusters (six-way replication). The volume is **always encrypted**; you can choose the encryption key but cannot disable encryption.

**Advantages:**
- **Simpler than provisioned** — removes much of the DB-instance/capacity management.
- **Scalable** — seamlessly scales compute/memory with no disruption to client connections.
- **Cost-effective** — pay only for database resources consumed, per-second.
- **Highly available storage** — fault-tolerant distributed storage with six-way replication.

**Designed for:** infrequently used applications, new applications (uncertain sizing), variable workloads, unpredictable workloads, development/test databases (auto-shutdown nights/weekends), and multi-tenant applications.

**Scaling behavior:**
- Scale up trigger: metrics must exceed limits for **1.5 minutes**.
- Scale down trigger: metrics must fall below limits for **5 minutes**.
- Cool-down between scaling: **5 minutes** (scale up), **15 minutes** (scale down).
- Scaling requires finding a "scaling point," which can be delayed by long-running transactions.
- Scaling is transparent to clients — existing connections and session state transfer to new nodes.
- Pause/resume adds higher latency on the first connection, typically ~**25 seconds**.

**How to provision:** AWS Console → Amazon RDS → **Create database** → on **Engine options**, choose **Serverless** for **Capacity type** → choose the capacity settings for your use case.

## Conversion notes
- This is Aurora Serverless **v1** specifically; consider it for spiky/intermittent target workloads where a provisioned cluster would be over-provisioned.
- Long-running transactions can delay scaling (the service must find a scaling point) — relevant for batch/ETL-style Oracle workloads being migrated.
- Encryption at rest is mandatory and always on.
- First-connection latency after a pause (~25s) matters for latency-sensitive apps; pair with RDS Proxy / connection pooling to mitigate connection churn.
- See: Amazon Aurora Serverless, "Aurora Serverless MySQL Generally Available," and "Amazon Aurora PostgreSQL Serverless Now Generally Available."
