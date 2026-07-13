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
