# Intake — sqlserver-pg18-20261030 (SQL Server → Aurora PostgreSQL 18)

| Item | Value |
|---|---|
| Purpose | Release test of the playbook refresh and context wiring; refreshes `sample-run-sqlserver-to-pg/` |
| Source | SQL Server 2022 (RDS, 16.0.4295.3), database `BobsUsedBookStore`, schema `dbo` (collation `SQL_Latin1_General_CP1_CI_AS`), loaded from the workshop scripts |
| Target | Aurora PostgreSQL **18.6** (Serverless v2), database `bookstore`, schema `dbo` |
| Connections | connections file outside the repo; passwords `${MS_PASSWORD}` / `${PG18_PASSWORD}` from AWS Secrets Manager per command |
| Scope | 20 tables, 4 views, 7 scalar functions, 14 procedures (+ data) |
| Strategy | full; testing data path `framework` |
| DMS SC already run? | No — converted from scratch |
| Decisions carried from the previous sample | `case_insensitive_collation` → option (a) `citext` on the searched columns (on PG 18 option (b), an ICU nondeterministic collation, now also supports `LIKE` — verified — recorded for the owner) |
| Gates | approved in advance by the user for this test run |
