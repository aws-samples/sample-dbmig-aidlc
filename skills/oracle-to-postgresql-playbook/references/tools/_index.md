# Tools & Services — Reference Index

Distilled from the AWS *Oracle Database 19c to Amazon Aurora PostgreSQL Migration Playbook* (Tools and services chapter). Reference only — test everything in a non-production environment first.

| File | Summary |
|---|---|
| [native-tools.md](native-tools.md) | **Informational.** Native clients (`sqlplus`/SQLcl, `psql`/`pg_dump`) for manual inspection. dbmig does NOT use them — it connects via Python drivers (oracledb thin + psycopg). |
| [aws-sct.md](aws-sct.md) | AWS Schema Conversion Tool — Java utility that connects to source/target, assesses the Oracle schema, and auto-converts objects to Aurora PostgreSQL; full download/configure/new-project walkthrough. |
| [sct-action-code-index.md](sct-action-code-index.md) | Automation-level legend (★ ratings), the per-topic AWS SCT action-code catalog, and a table of codes whose limitation no longer exists on Aurora PostgreSQL 18 (MERGE, SKIP LOCKED, GROUPING SETS, …). |
| [aws-dms.md](aws-dms.md) | AWS Database Migration Service — managed data migration/replication with near-zero source downtime; CDC, KMS/SSL/Secrets Manager security. **PG 17/18 targets need DMS engine 3.5.4+.** DMS Schema Conversion and DMS Serverless. |
| [rds-on-outposts.md](rds-on-outposts.md) | Amazon RDS on Outposts — managed RDS (SQL Server/MySQL/PostgreSQL) on premises for hybrid/low-latency/data-residency needs. Note: NOT supported with Aurora. |
| [rds-proxy.md](rds-proxy.md) | Amazon RDS Proxy — fully managed connection-pooling proxy; cuts failover time up to ~66% ([AWS RDS Proxy](https://aws.amazon.com/rds/proxy/)), integrates with Secrets Manager/IAM; session-pinning caveat for converted code. |
| [aurora-serverless-v1.md](aurora-serverless-v1.md) | **Aurora Serverless v2** (v1 reached end of life 2025-03-31; filename kept) — ACU-based autoscaling 0–256 ACU, scale-to-zero, mixing with provisioned instances. |
