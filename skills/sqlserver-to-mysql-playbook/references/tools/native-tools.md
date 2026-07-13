# Native Client Tools vs. dbmig Connectivity (Informational)

> Informational note for the dbmig-aidlc framework — not part of the AWS playbook.

The AWS playbook tooling pages reference native and AWS-managed tools (AWS SCT with JDBC drivers, AWS DMS, `sqlcmd`/`bcp` for SQL Server, the `mysql` client for MySQL). This note clarifies how the **dbmig** toolkit connects, so there is no confusion when following playbook steps.

## How dbmig connects — pure Python drivers
The `dbmig` toolkit (`scripts/dbmig/`) connects to databases using **Python drivers only** — no native client tools required:

- **SQL Server (source):** [`python-tds`](https://python-tds.readthedocs.io/) (pure Python, package `pytds`).
- **MySQL / Aurora MySQL (target):** [`PyMySQL`](https://pymysql.readthedocs.io/) (pure Python).

## What dbmig does NOT use
- It does **not** use `sqlcmd` or `bcp` (SQL Server native client tools).
- It does **not** use the `mysql` command-line client or `mysqldump`.
- It does **not** require AWS SCT or AWS DMS to function for connectivity, inventory, schema apply, data copy, reconcile, or tests. (SCT/DMS remain valid AWS-managed alternatives and are documented in the playbook for production-scale workflows.)

## Relationship to the playbook tools
- **AWS SCT** (see `aws-sct.md`, `action-code.md`) is the AWS GUI conversion tool. In the dbmig framework, **Kiro performs the schema/code conversion** via the construction skill; the SCT action-code index is injected as **reference context** only, not executed.
- **AWS DMS** (see `aws-dms.md`) is the recommended path for production-scale data movement; dbmig's built-in `migrate-data` (PyMySQL/pytds-based) is intended for dev/test loads and reconciliation, and the framework hands off to DMS for production.
- The Aurora/RDS feature pages (RDS Proxy, Serverless, Backtrack, Parallel Query, RDS on Outposts) are **target-side capabilities** — informational for planning the Aurora MySQL target, with no bearing on how dbmig connects.

## Practical implication
You can run all dbmig connectivity and data steps with only `pip install -r scripts/requirements.txt` — no SQL Server or MySQL native client install needed:

```bash
pip install -r scripts/requirements.txt
python -m dbmig test-connection --side both   # exits non-zero on failure
```
