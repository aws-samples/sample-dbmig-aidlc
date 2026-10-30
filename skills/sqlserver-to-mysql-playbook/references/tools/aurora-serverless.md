# Amazon Aurora Serverless Overview (v2; v1 retired)

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.auroraserverless.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A — target deployment/capacity option.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Rewritten for Aurora Serverless v2 (v1 reached end of life 2025-03-31); facts verified on the validation clusters.

## SQL Server
N/A on the source side. Presented as a target deployment model to consider when migrating off SQL Server.

## MySQL

**Aurora Serverless v1 reached end of life on 2025-03-31.** Use **Aurora Serverless v2**, an instance class (`db.serverless`) for Aurora MySQL 3 and 8.4; both validation clusters for this review were Serverless v2. The filename is kept so links resolve; the Oracle→MySQL playbook page `../../../oracle-to-mysql-playbook/references/tools/aurora-serverless-v1.md` has the full description.

## Conversion notes
- **Capacity:** min 0 or 0.5 ACU to max 256 ACU per instance (1 ACU ≈ 2 GiB memory + CPU + network); scales in fine-grained steps within seconds while connections stay open.
- **Auto-pause:** `MinCapacity=0` pauses an idle instance (storage-only cost); the first connection after a pause waits for the resume.
- **Mixed clusters:** provisioned writer + serverless readers or the reverse; readers in promotion tier 0–1 scale with the writer.
- **Same features** as provisioned Aurora MySQL 3 / 8.4: Multi-AZ, Global Database, RDS Proxy, Data API, Backtrack.
- **Capacity-derived settings:** `max_connections` (135 at a 4 ACU maximum, verified) and buffer pool size follow capacity; `performance_schema` is off by default (verified).
- **Sizing from SQL Server:** derive `MaxCapacity` from the source's peak CPU/memory (Perfmon, `sys.dm_os_*`) and `MinCapacity` from the steady baseline; compare cost against provisioned instances for steady heavy load.
- The v1 notes (ACU doubling, 1.5/5-minute thresholds, 5/15-minute cooldowns, ~25 s resume) no longer apply.
