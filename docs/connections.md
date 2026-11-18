# Connecting to databases — pure Python, no native tools

The `dbmig` toolkit (`scripts/dbmig/`) connects with **Python drivers** — no `sqlplus` or
`psql` install required:

- **Oracle (source)**: [`oracledb`](https://python-oracledb.readthedocs.io/) in *thin mode*
  (Oracle 12.1+). **Oracle 11.2** is supported in *thick mode*: set `driver_mode: thick` on
  the source connection and install Oracle Instant Client 19+ (x86-64 Linux/Windows, or an
  Intel Mac; Apple Silicon has no Instant Client that reaches 11.2)
- **SQL Server (source)**: [`python-tds`](https://python-tds.readthedocs.io/) (pure Python),
  SQL Server **2008** and later
- **PostgreSQL (target)**: [`psycopg`](https://www.psycopg.org/) v3 with bundled libpq
- **MySQL (target)**: [`PyMySQL`](https://pymysql.readthedocs.io/) — pure Python

```bash
# one-time: an isolated virtual environment inside the repo (see the README's Getting started)
python3 -m venv .venv && .venv/bin/pip install -e scripts/
./dbmig test-connection --side both     # exits non-zero on failure
```

Run every command through the **`./dbmig`** launcher at the repo root. It uses the repo's
`.venv` automatically (no `activate` needed), so config and `migrations/` resolve from the repo
root. With the venv activated, the plain `dbmig` command works too. `--conn <path>` /
`--config <path>` (before the command) point at a connections file / migration config
elsewhere.

## The connections file

Copy `templates/connections.example.yaml` to `connections.yaml` (git-ignored) and fill in the
`source` and `target` sections. Keep passwords out of the file: use environment-variable
references such as `password: ${ORA_PASSWORD}`, expanded at run time. The template documents
every field, including TLS (`protocol: tcps` on the source, `sslmode` on the target) and the
Oracle 11.2 thick-mode settings. Set `target.version`: version-specific conversion defaults
depend on it.

## Credentials in AWS Secrets Manager

`connections.yaml` needs no special support: give Kiro the secret name and AWS profile/region and
it reads the secret with the AWS CLI, writes the non-secret fields (host, port, user,
service/database) into `connections.yaml`, and keeps the password as a `${VAR}` reference supplied
from the secret per command — it is never written to disk or echoed.

## Database users

[`guides/database-users-and-permissions.md`](../guides/database-users-and-permissions.md) shows
how to create a least-privilege read-only source user and a read-write target user, and the extra
permissions for the PostgreSQL FDW data-load method.
