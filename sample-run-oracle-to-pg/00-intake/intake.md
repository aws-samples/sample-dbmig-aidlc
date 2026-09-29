# Intake — demo-migration (Oracle → Aurora PostgreSQL)

| Item | Value |
|---|---|
| Source | Oracle 19c EE, schema `DEMO` (login user `<source-user>` ≠ owner — session schema set by run-tests) |
| Target | Aurora PostgreSQL 17.7, database `<target-db>`, schema `demo` |
| Connections | `connections.yaml` — non-secret fields filled from AWS Secrets Manager via the AWS CLI; passwords are `${ORA_PASSWORD}` / `${PG_PASSWORD}` supplied per command |
| Scope | all tables, indexes, constraints, identity sequences, functions, procedures, packages, triggers |
| Strategy | full (schema + code + data) — testing data path: `framework` (`dbmig migrate-data`) |
| DMS SC already run? | No — converted from scratch |
| Toolkit | repo-local `.venv`, every command via `./dbmig` |
