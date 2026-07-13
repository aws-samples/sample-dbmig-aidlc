# Management — SQL Server → Aurora PostgreSQL Migration Playbook references

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> Base URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/

Distilled reference files for the **Management** chapter. Each file follows a fixed structure (topic title, source/URL, conversion category, SCT automation, SQL Server, PostgreSQL, conversion notes).

| File | Topic | Feature compatibility | Primary AWS replacement |
|---|---|---|---|
| [sql-server-agent.md](sql-server-agent.md) | SQL Server Agent and PostgreSQL | N/A | Scheduled AWS Lambda (CloudWatch Events) |
| [alerting.md](alerting.md) | Alerting features | One-star | Amazon RDS event notifications + Amazon SNS |
| [database-mail.md](database-mail.md) | Database mail features | One-star | AWS Lambda + Amazon SES |
| [etl.md](etl.md) | ETL features | None | AWS Glue (+ S3, CloudWatch) |
| [export-import.md](export-import.md) | Export and import features | None | `pg_dump` / `pg_restore` / `COPY` + Amazon S3 |
| [server-logs.md](server-logs.md) | Viewing server logs | Three-star | RDS console / API / CLI / SDKs |
| [maintenance-plans.md](maintenance-plans.md) | Maintenance plans | Three-star | RDS snapshots + `VACUUM`/`ANALYZE`/`REINDEX` |
| [monitoring.md](monitoring.md) | Monitoring features | Three-star | Amazon CloudWatch + Performance Insights |
| [resource-governor.md](resource-governor.md) | Resource governor features | Three-star | Multiple Aurora instances / replicas; parallelism + session controls |
| [linked-servers.md](linked-servers.md) | Linked servers | Three-star | `dblink` / `postgres_fdw` |
| [scripting.md](scripting.md) | Scripting features | None | pgAdmin, AWS CLI, Amazon RDS API/SDKs |

## Cross-cutting themes

- **No in-engine scheduler/agent**: SQL Server Agent jobs, Database Mail, and maintenance scheduling are replaced by scheduled AWS Lambda + Amazon CloudWatch Events, Amazon SES, Amazon SNS, and Amazon RDS automated snapshots.
- **Managed service tooling**: SSMS/PowerShell/SQLCMD administration maps to pgAdmin, `psql`, the AWS Console, AWS CLI, and the Amazon RDS API/SDKs.
- **Observability**: SQL Server Profiler/Extended Events/Query Store and DMVs map to Amazon CloudWatch, Enhanced Monitoring, AWS Performance Insights, and `pg_stat_*` views.
- **Heterogeneous data access**: linked servers map to `dblink` / `postgres_fdw`; SSIS/DTS ETL maps to AWS Glue (convertible via AWS SCT).
