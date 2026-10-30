# Intake — oracle-pg18-20261030 (Oracle → Aurora PostgreSQL 18)

| Item | Value |
|---|---|
| Purpose | Release test of the playbook refresh and context wiring; refreshes `sample-run-oracle-to-pg/` |
| Source | Oracle 19c EE (RDS), schema `DEMO` (login user `<source-user>` ≠ owner) |
| Target | Aurora PostgreSQL **18.6** (Serverless v2), database `demodb`, schema `demo` |
| Connections | connections file outside the repo; non-secret fields literal, passwords `${ORA_PASSWORD}` / `${PG18_PASSWORD}` from AWS Secrets Manager per command |
| Scope | all tables, indexes, constraints, identity sequences, functions, procedures, packages, triggers |
| Strategy | full (schema + code + data); testing data path `framework` (`dbmig migrate-data`) |
| DMS SC already run? | No — converted from scratch |
| Decisions carried from the previous sample | `fulltext_redesign` → tsvector + GIN (option A); datatype defaults per `engines/oracle-to-postgresql/datatype-map.yaml` |
| Gates | approved in advance by the user for this test run ("approval all") |
| Toolkit | repo-local `.venv`, every command via `./dbmig` |
