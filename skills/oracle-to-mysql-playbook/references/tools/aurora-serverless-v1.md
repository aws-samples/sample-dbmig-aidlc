# Amazon Aurora Serverless (v2; v1 retired)

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tools.auroraserverless.html

**Conversion category:** N/A (Aurora deployment / capacity option)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): **Aurora Serverless v1 reached end of life on 2025-03-31.** This page now describes **Aurora Serverless v2**, the only serverless option for Aurora MySQL 3 and 8.4. The filename is kept so existing links still resolve. Both validation clusters for this review were Serverless v2.

## Oracle
Not an Oracle feature. Relevant when sizing the target: instead of provisioning fixed capacity for an Oracle instance, the Aurora MySQL cluster can scale compute on demand.

## Aurora MySQL — Aurora Serverless v2
Serverless v2 is an instance class (`db.serverless`) inside a normal Aurora cluster. Capacity is measured in **Aurora Capacity Units (ACUs)**, about 2 GiB of memory each with matching CPU and network. You set a minimum and maximum per cluster; capacity changes in fine-grained steps within seconds while connections stay open.

- **Range:** minimum **0** or 0.5 ACU, maximum up to **256 ACU** per instance.
- **Scale to zero (auto-pause):** with `MinCapacity=0` an idle instance pauses and costs only storage. The first connection after a pause waits (or, through the Data API, fails until the instance resumes). Use `MinCapacity ≥ 0.5` for latency-sensitive workloads.
- **Mix with provisioned instances:** provisioned writer + Serverless v2 readers, or the reverse. Readers in promotion tiers 0–1 scale with the writer so they can take over after failover.
- **Same engine features** as provisioned Aurora MySQL 3 / 8.4: Multi-AZ, Global Database, RDS Proxy, Data API, Backtrack, zero-ETL integrations.
- **Capacity-dependent settings:** `max_connections` is derived from the maximum ACU (135 at 0.5–4 ACU, verified on both versions); InnoDB buffer pool size follows capacity. `performance_schema` is off by default (verified) and is a static parameter.

```bash
aws rds create-db-cluster --db-cluster-identifier app --engine aurora-mysql \
  --engine-version 8.4.mysql_aurora.8.4.8 \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=64 \
  --manage-master-user-password --storage-encrypted --enable-http-endpoint ...
aws rds create-db-instance --db-instance-identifier app-1 --db-cluster-identifier app \
  --engine aurora-mysql --db-instance-class db.serverless --no-publicly-accessible
```

**Good fits:** variable or unpredictable workloads, new applications with uncertain sizing, dev/test (scale to zero overnight), many small per-tenant databases, and readers that absorb reporting spikes.

## Conversion notes
- Do not plan new targets on Serverless v1; it no longer exists. Old guidance about v1 scaling points, ACU doubling, 5/15-minute cool-downs and ~25 s resume latency does not apply to v2.
- Size `MaxCapacity` from the Oracle AWR peak (CPU and memory) and `MinCapacity` from the steady baseline. Watch the `ACUUtilization` and `ServerlessDatabaseCapacity` CloudWatch metrics during performance tests.
- Long batch jobs migrated from Oracle can hold the instance at max ACU for hours; compare cost with a provisioned (or I/O-Optimized) writer for steady heavy load.
- Storage encryption is chosen at creation; create encrypted clusters.
- Pair with RDS Proxy or the Data API for connection-heavy serverless applications.
