# Tools & Services — Reference Index

Distilled from the AWS Oracle→Aurora MySQL Migration Playbook (Migration tools and services chapter). These pages cover the AWS tooling and Aurora MySQL features used around a migration, plus the AWS SCT per-feature automation reference.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29). Target-version baseline: `../target-baseline-aurora-mysql.md`.

| File | Summary |
|---|---|
| [aws-sct.md](aws-sct.md) | AWS SCT — project walkthrough; SCT/DMS SC generate Aurora MySQL 8.0 code, so modernize 5.7-era workarounds and check 8.4 breaks. |
| [sct-action-code-index.md](sct-action-code-index.md) | AWS SCT automation levels and action codes, plus a verified table of codes whose limitation no longer exists on Aurora MySQL 3 / 8.4. |
| [aws-dms.md](aws-dms.md) | AWS DMS — data movement + CDC; supports MySQL 8.0 and 8.4 targets; DMS Schema Conversion targets Aurora MySQL 8.0.32 only. |
| [rds-on-outposts.md](rds-on-outposts.md) | Amazon RDS on Outposts — managed RDS (SQL Server/MySQL/PostgreSQL) on-premises for low-latency/data-residency needs; not supported with Aurora. |
| [rds-proxy.md](rds-proxy.md) | Amazon RDS Proxy — fully managed connection-pooling proxy that improves scalability and cuts failover time by up to 66% ([AWS RDS Proxy](https://aws.amazon.com/rds/proxy/)); integrates with Secrets Manager/IAM, no code changes. |
| [aurora-serverless-v1.md](aurora-serverless-v1.md) | Aurora Serverless **v2** (v1 reached end of life 2025-03-31): 0–256 ACU, auto-pause, mixed with provisioned instances. |
| [aurora-parallel-query.md](aurora-parallel-query.md) | Aurora Parallel Query — storage-layer push-down for analytics; on 3 / 8.4 works with partitioned tables and LOB/JSON columns; not with I/O-Optimized or t2/t3; off by default. |
| [aurora-backtrack.md](aurora-backtrack.md) | Aurora Backtrack — rewinds a whole cluster (up to 72h) on versions 2, 3 and 8.4; enable at creation; conflicts with binlog replicas and cross-Region replicas. |
