# Intake — BobsUsedBookStore (SQL Server → Aurora PostgreSQL)

| Item | Value |
|---|---|
| Source | SQL Server 2022 (RDS), database `BobsUsedBookStore`, schema `dbo` (collation `SQL_Latin1_General_CP1_CI_AS`) |
| Target | Aurora PostgreSQL 17.7, database `<target-db>`, schema `dbo` |
| Connections | non-secret fields from AWS Secrets Manager via the AWS CLI; passwords as `${VAR}` references |
| Scope | 20 tables, 4 views, 7 scalar functions, 14 procedures (+ data) |
| Strategy | full — testing data path `framework` (`dbmig migrate-data`) |
| DMS SC already run? | No — converted from scratch |
