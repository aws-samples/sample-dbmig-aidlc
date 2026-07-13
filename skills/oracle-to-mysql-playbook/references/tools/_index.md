# Tools & Services — Reference Index

Distilled from the AWS Oracle→Aurora MySQL Migration Playbook (Migration tools and services chapter). These pages cover the AWS tooling and Aurora MySQL features used around a migration, plus the AWS SCT per-feature automation reference.

| File | Summary |
|---|---|
| [aws-sct.md](aws-sct.md) | AWS Schema Conversion Tool — install/configure drivers, create a project, generate the assessment report, and convert/apply (or save-as-SQL) the Oracle schema to Aurora MySQL. |
| [sct-action-code-index.md](sct-action-code-index.md) | The full AWS SCT automation-level scale (★ to ★★★★★ / No automation) and the action codes per feature area (tables, constraints, data types, cursors, triggers, sequences, PLSQL, etc.). |
| [aws-dms.md](aws-dms.md) | AWS Database Migration Service — moves data (homogeneous/heterogeneous) with minimal downtime via source/target connections and tasks; pairs with AWS SCT for schema conversion. |
| [rds-on-outposts.md](rds-on-outposts.md) | Amazon RDS on Outposts — managed RDS (SQL Server/MySQL/PostgreSQL) on-premises for low-latency/data-residency needs; not supported with Aurora. |
| [rds-proxy.md](rds-proxy.md) | Amazon RDS Proxy — fully managed connection-pooling proxy that improves scalability and cuts failover time by up to 66% ([AWS RDS Proxy](https://aws.amazon.com/rds/proxy/)); integrates with Secrets Manager/IAM, no code changes. |
| [aurora-serverless-v1.md](aurora-serverless-v1.md) | Amazon Aurora Serverless v1 (and v2) — on-demand autoscaling capacity for intermittent/unpredictable workloads; v1 doubles ACUs, v2 scales incrementally and near-instantly. |
| [aurora-parallel-query.md](aurora-parallel-query.md) | Amazon Aurora Parallel Query — pushes analytical query processing into the storage layer across thousands of CPUs; constraints on row format, partitions, and TEXT/BLOB/GEOMETRY types. |
| [aurora-backtrack.md](aurora-backtrack.md) | Amazon Aurora Backtrack — rewinds a cluster in minutes to undo mistakes (up to 72h); must be enabled at creation, whole-cluster only, incompatible with binlog/cross-Region replication. |
