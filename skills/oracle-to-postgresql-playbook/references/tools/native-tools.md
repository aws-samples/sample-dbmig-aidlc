# Native Client Tools (sqlplus / SQLcl / psql) — informational

> Framework note (dbmig-aidlc). The `dbmig` Python package does **not** use native client
> tools. It connects directly with Python drivers — `oracledb` (thin mode) for Oracle and
> `psycopg` (v3, bundled libpq) for PostgreSQL — so no `sqlplus`/`psql` install is required.
>
> This page is **informational only**, for operators who want to inspect either side
> manually outside the toolkit. It is not part of the dbmig execution path.

**Conversion category:** N/A (tooling)

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PG 18 client binaries, TLS default, Data API as a no-network option.

## Oracle (source) — SQL*Plus / SQLcl (manual inspection)
- `sqlplus user/pass@//host:port/service` — connect; `sqlplus -V` for version.
- `SELECT DBMS_METADATA.GET_DDL('TABLE','EMP','APP') FROM dual;` — view DDL (dbmig uses the
  same `DBMS_METADATA` calls through `oracledb`).
- SQLcl (`sql`) is the modern equivalent with a built-in `DDL` command.

## PostgreSQL / Aurora (target) — psql (manual inspection)
- `psql "postgresql://user:pass@host:port/db?sslmode=require"` — connect; `psql --version`.
- `\copy schema.table FROM 'data.csv' ...` — manual load (dbmig uses the COPY protocol via
  `psycopg` instead).
- `pg_dump` / `pg_restore` for manual schema/data export.

## Conversion notes
- In dbmig, connectivity, DDL extraction, apply, data COPY, and reconciliation are all done
  through the Python drivers — see `./dbmig test-connection`, `inventory`,
  `apply-schema`, `migrate-data`, `compare`.
- Use `sslmode=verify-full` with the RDS CA bundle (or at least `sslmode=require`) for Aurora endpoints; Aurora PostgreSQL 18 enforces TLS by default (`rds.force_ssl = 1`).
- Use **PostgreSQL 18 client binaries** (`psql`, `pg_dump`, `pg_restore`) against an Aurora PostgreSQL 18 target. Older `pg_dump` versions refuse to dump a newer server.
- For ad-hoc SQL without network access to port 5432, the **RDS Data API** (`aws rds-data execute-statement`, enabled with `--enable-http-endpoint`) works over HTTPS with IAM. This review validated every PG 18 claim through it. dbmig reads connection details
  from `connections.yaml` with `${ENV_VAR}` expansion; never put plaintext passwords in
  shell history.
