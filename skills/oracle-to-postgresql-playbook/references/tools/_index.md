# Tools & Services — Reference Index

Distilled from the AWS *Oracle Database 19c to Amazon Aurora PostgreSQL Migration Playbook* (Tools and services chapter). Reference only — test everything in a non-production environment first.

| File | Summary |
|---|---|
| [native-tools.md](native-tools.md) | **Informational.** Native clients (`sqlplus`/SQLcl, `psql`/`pg_dump`) for manual inspection. dbmig does NOT use them — it connects via Python drivers (oracledb thin + psycopg). |
| [aws-sct.md](aws-sct.md) | AWS Schema Conversion Tool — Java utility that connects to source/target, assesses the Oracle schema, and auto-converts objects to Aurora PostgreSQL; full download/configure/new-project walkthrough. |
| [sct-action-code-index.md](sct-action-code-index.md) | Automation-level legend (★ ratings) plus the full per-topic AWS SCT action-code catalog (SQL, tables, data types, cursors, triggers, sequences, views, UDTs, merge, matviews, hints, DB links, indexes, partitioning, OLAP, etc.). |
| [aws-dms.md](aws-dms.md) | AWS Database Migration Service — managed data migration/replication with near-zero source downtime; homogeneous and heterogeneous migrations, CDC, KMS/SSL/Secrets Manager security. Pairs with SCT (SCT=schema, DMS=data). |
| [rds-on-outposts.md](rds-on-outposts.md) | Amazon RDS on Outposts — managed RDS (SQL Server/MySQL/PostgreSQL) on premises for hybrid/low-latency/data-residency needs. Note: NOT supported with Aurora. |
| [rds-proxy.md](rds-proxy.md) | Amazon RDS Proxy — fully managed connection-pooling proxy; cuts failover time up to ~66% ([AWS RDS Proxy](https://aws.amazon.com/rds/proxy/)), integrates with Secrets Manager/IAM, no app code changes; GA for Aurora/RDS MySQL & PostgreSQL. |
| [aurora-serverless-v1.md](aurora-serverless-v1.md) | Amazon Aurora Serverless v1 — on-demand autoscaling Aurora capacity for intermittent/unpredictable workloads; per-second billing, always-encrypted storage, scaling thresholds and pause/resume behavior. |
