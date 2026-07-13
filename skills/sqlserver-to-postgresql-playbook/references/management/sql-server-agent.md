# SQL Server Agent and PostgreSQL

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.scheduledlambda.html

**Conversion category:** N/A
**SCT automation:** N/A

## SQL Server

SQL Server Agent provides two main functions: scheduling automated maintenance jobs and alerting. Other SQL Server built-in frameworks, such as replication, also rely on SQL Server Agent jobs.

See the related Maintenance Plans and Alerting topics for the job and alert capabilities Agent drives.

## PostgreSQL

There is currently no equivalent in Amazon Aurora PostgreSQL-Compatible Edition for scheduling tasks. To schedule work, create a scheduled AWS Lambda function that runs a stored procedure.

Example pattern (scheduled Lambda triggered by Amazon CloudWatch Events on a rate/cron schedule, invoking SQL against the cluster) — see the Database Mail topic for a full walkthrough of the scheduled-Lambda approach:

```text
CloudWatch Events (rate/cron) -> AWS Lambda -> psycopg2 connection -> run stored procedure / query
```

## Conversion notes

- No native scheduler exists in Aurora PostgreSQL; replace SQL Server Agent jobs with scheduled AWS Lambda functions triggered by Amazon CloudWatch Events (rate or cron expressions).
- Replace Agent alerting with Amazon RDS event notifications + Amazon SNS (see Alerting).
- Replace Agent-driven maintenance jobs with RDS automated snapshots and SQL maintenance commands (`VACUUM`, `ANALYZE`, `REINDEX`) — see Maintenance Plans.
- You pay per Lambda invocation, so choose schedule intervals accordingly.
