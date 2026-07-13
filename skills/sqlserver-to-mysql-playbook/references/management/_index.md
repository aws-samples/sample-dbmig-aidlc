# Management features — SQL Server → Aurora MySQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.management.html

Reference files distilled from the *Migrating management features to Aurora MySQL* chapter, covering job scheduling, event notifications, email, ETL, logging, maintenance, monitoring, resource management, linked servers, and scripting.

| File | Topic | Conversion category | Primary AWS replacement |
|---|---|---|---|
| [agent.md](agent.md) | SQL Server Agent and MySQL Agent | Manual (no compatibility) | Aurora MySQL Events + CloudWatch Events/Lambda |
| [alerting.md](alerting.md) | Alerting features | Manual (one star) | Amazon RDS event notifications via Amazon SNS |
| [database-mail.md](database-mail.md) | Database mail features | Manual (one star) | AWS Lambda integration / SNS / queue table |
| [etl.md](etl.md) | ETL features | Manual (one star) | AWS Glue |
| [server-logs.md](server-logs.md) | Viewing server logs | Automatic (three star) | RDS console / API / CLI / SDKs |
| [maintenance-plans.md](maintenance-plans.md) | Maintenance plans | Automatic (three star) | RDS automated backups/snapshots + SQL maintenance |
| [monitoring.md](monitoring.md) | Monitoring features | Automatic (three star) | Amazon CloudWatch + RDS Performance Insights |
| [resource-governor.md](resource-governor.md) | Resource governor features | Manual (one star) | Aurora MySQL User Resource Limit Options |
| [linked-servers.md](linked-servers.md) | Linked servers | Manual (no compatibility) | Custom application solution |
| [scripting.md](scripting.md) | Scripting features | Manual (no compatibility) | MySQL Workbench, RDS API, AWS Console, AWS CLI |

## Summary of key migration themes

- **Scheduling & jobs**: SQL Server Agent has no Aurora MySQL equivalent. Use in-cluster Aurora MySQL Events for single-cluster scheduling, or CloudWatch Events + Lambda / EC2 cron for orchestration.
- **Alerting & email**: Replace Agent alerts and Database Mail with Amazon SNS event notifications, CloudWatch alarms, and AWS Lambda (or a queue-table pattern for application email).
- **ETL**: SSIS/DTS → AWS Glue (no automated package migration; rewrite required).
- **Logging & monitoring**: Strong compatibility — use RDS console/API/CLI for logs and Amazon CloudWatch + Performance Insights for monitoring.
- **Maintenance**: RDS-managed automated backups/snapshots; table maintenance via `OPTIMIZE TABLE`, `ALTER TABLE … FORCE`, `CHECK TABLE`, and `innodb_stats_auto_recalc`.
- **Resource management**: Resource Governor → per-user resource limits (errors rather than throttling; needs app changes).
- **Linked servers**: No equivalent — re-implement cross-instance access in the application layer.
- **Scripting**: No PowerShell/SMO/SQLCMD equivalent — use MySQL Workbench, AWS CLI, and the RDS API.
