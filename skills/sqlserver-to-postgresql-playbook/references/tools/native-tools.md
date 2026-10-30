# Native client tools — not used by dbmig (informational)

> Informational note. Not a playbook page.

The `dbmig` toolkit connects to databases using **pure Python drivers** — it does **not**
shell out to native client tools.

| Side | dbmig driver | Native tools NOT used |
|---|---|---|
| SQL Server (source) | [`pytds`](https://pypi.org/project/python-tds/) (`python-tds`) | `sqlcmd`, `bcp` |
| PostgreSQL (target) | [`psycopg`](https://www.psycopg.org/) v3 | `psql` |

Implications:
- No SQL Server or PostgreSQL native client install is required to run `dbmig`.
- Connection tests, inventory, extraction, DDL apply, data copy, reconciliation, and
  test execution all go through the Python driver layer.
- The AWS tools described in this `tools/` directory (AWS SCT, AWS DMS, RDS Proxy, RDS on
  Outposts, Aurora Serverless v1) are **AWS-managed services / GUI utilities** referenced
  by the playbook. They are separate from `dbmig`'s Python-driver path and are documented
  here for context and hand-off (e.g. production data movement via AWS DMS).

For manual inspection outside `dbmig`, use **PostgreSQL 18 client binaries** (`psql`, `pg_dump`) against an Aurora PostgreSQL 18 target. Connect with `sslmode=verify-full` (TLS is required by default via `rds.force_ssl = 1`). Without network access to port 5432, use the **RDS Data API** (`aws rds-data execute-statement`). This review validated all PG 18 statements through it.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): added PG 18 client, TLS and Data API notes.
