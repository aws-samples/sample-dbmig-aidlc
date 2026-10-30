# Amazon Aurora Serverless (v2) — formerly "Aurora Serverless v1"

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook (original topic: Aurora Serverless v1)
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tools.auroraserverless.html

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): **Aurora Serverless v1 reached end of life on 2025-03-31.** Remaining v1 clusters were moved to Serverless v2 ([AWS docs](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless.relnotes.html)). This page now describes **Aurora Serverless v2**, the only serverless option for Aurora PostgreSQL 18. The filename is kept so existing links still resolve.

**Conversion category:** N/A (target deployment/capacity option)
**SCT automation:** N/A

## Oracle
Not an Oracle feature. Conceptually relevant when sizing the target: instead of manually provisioning fixed capacity (as with a traditional Oracle instance), the target Aurora cluster can autoscale on demand.

## PostgreSQL — Aurora Serverless v2
Aurora Serverless v2 is an instance class (`db.serverless`) inside a normal Aurora cluster. Capacity is measured in **Aurora Capacity Units (ACUs)**, about 2 GiB of memory each with matching CPU and network. You set a minimum and maximum per cluster, and capacity changes in fine-grained steps within seconds, while connections stay open.

Facts that matter for a migration target (the validation cluster for this review was itself Serverless v2 on Aurora PostgreSQL 18.6):
- **Range:** minimum **0** or 0.5 ACU, maximum up to **256 ACU** per instance.
- **Scale to zero (auto-pause):** with `MinCapacity=0` an idle instance pauses and costs only storage. The first request after a pause fails until the instance resumes (observed: Data API `resuming after being auto-paused. Please wait a few seconds and try again`). Use `MinCapacity ≥ 0.5` for anything latency-sensitive, and add client retry logic otherwise.
- **Mix with provisioned instances:** a cluster can have a provisioned writer and Serverless v2 readers, or the reverse. Readers in promotion tiers 0–1 scale with the writer, so they can take over after a failover.
- **Same engine and features** as provisioned Aurora PostgreSQL 18: Multi-AZ, Global Database, RDS Proxy, Data API, Performance/Database Insights, all extensions.
- **Storage** is the same six-way replicated cluster volume, always encrypted when created encrypted (choose a KMS key at creation).
- Memory-sensitive settings scale with capacity. `shared_buffers` follows the **maximum** ACU, so a very low max can hurt cache-heavy workloads.

```bash
aws rds create-db-cluster --db-cluster-identifier app --engine aurora-postgresql --engine-version 18.6 \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=64 \
  --manage-master-user-password --storage-encrypted --enable-http-endpoint ...
aws rds create-db-instance --db-instance-identifier app-1 --db-cluster-identifier app \
  --engine aurora-postgresql --db-instance-class db.serverless --no-publicly-accessible
```

**Good fits:** variable or unpredictable workloads, new applications with uncertain sizing, dev/test (scale to zero overnight), many small per-tenant databases, and readers that absorb reporting spikes.

## Conversion notes
- Do not plan new targets on Serverless v1; it no longer exists. Old guidance about v1 scaling points, 5/15-minute cool-downs and ~25 s resume latency does not apply to v2.
- Size `MaxCapacity` from the Oracle AWR peak (CPU and memory), and `MinCapacity` from the steady baseline. Watch the `ACUUtilization` and `ServerlessDatabaseCapacity` CloudWatch metrics during performance tests.
- Long-running batch jobs migrated from Oracle can push the instance to max ACU for hours. Compare the cost against a provisioned (or I/O-Optimized) writer for steady heavy workloads.
- Pair with RDS Proxy or the Data API for connection-heavy serverless applications.
