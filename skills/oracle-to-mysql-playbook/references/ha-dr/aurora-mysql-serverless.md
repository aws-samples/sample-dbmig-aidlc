# Migrate to Aurora MySQL Serverless

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.hadr.serverless.html

**Conversion category:** N/A (infrastructure / deployment-option topic)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Rewritten for Aurora Serverless v2 (v1, which this page described, reached end of life 2025-03-31); key v2 facts verified on the validation clusters.

## Oracle

(No direct Oracle feature equivalent.) The playbook positions Aurora Serverless as a cost-efficient alternative to running Oracle RAC for infrequent, intermittent, or unpredictable workloads — you avoid managing/provisioning fixed cluster hardware and avoid paying for unused capacity.

## MySQL

> **Correction:** the original page described **Aurora Serverless v1** (MySQL 5.6/5.7 only), which reached end of life on 2025-03-31. Use **Aurora Serverless v2**, an instance class (`db.serverless`) that works with Aurora MySQL 3 and 8.4 — both validation clusters for this review were Serverless v2. Full details: `../tools/aurora-serverless-v1.md` (kept under its old filename).

Aurora Serverless v2 in short:
- Capacity in ACUs (about 2 GiB memory each with matching CPU), scaling in fine-grained steps within seconds between a minimum (0 or 0.5) and a maximum (up to 256) ACU per instance; connections stay open while it scales.
- Lives in a normal Aurora cluster: mix provisioned and serverless instances, use reader and cluster endpoints, Multi-AZ, Global Database, RDS Proxy, Data API.
- `MinCapacity = 0` enables auto-pause when idle (first connection after a pause waits for resume).
- `max_connections` and the buffer pool derive from capacity (`max_connections` = 135 at a 4 ACU maximum, verified).

The v1 capacity-unit table (2 CPU/4 GB … 256 CPU/488 GB), the invisible network load balancer and request routers, and "migrate between standard and serverless" no longer apply.

## Conversion notes
- Deployment-model choice, not a schema/code conversion — no SCT automation.
- Good fit for intermittent or unpredictable workloads and dev/test; for steady high-throughput OLTP compare against provisioned (or I/O-Optimized) instances.
- Compared with RAC: scale-up is automatic (capacity), scale-out is readers; there is still one writer.
