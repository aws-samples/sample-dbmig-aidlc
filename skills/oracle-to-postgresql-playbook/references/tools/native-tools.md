# Native Client Tools (sqlplus / SQLcl / psql) — informational

> Framework note (dbmig-aidlc). The `dbmig` Python package does **not** use native client
> tools. It connects directly with Python drivers — `oracledb` (thin mode) for Oracle and
> `psycopg` (v3, bundled libpq) for PostgreSQL — so no `sqlplus`/`psql` install is required.
>
> This page is **informational only**, for operators who want to inspect either side
> manually outside the toolkit. It is not part of the dbmig execution path.

**Conversion category:** N/A (tooling)

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
  through the Python drivers — see `python -m dbmig test-connection`, `inventory`,
  `apply-schema`, `migrate-data`, `compare`.
- Use `sslmode=require` (or stricter) for Aurora endpoints. dbmig reads connection details
  from `connections.yaml` with `${ENV_VAR}` expansion; never put plaintext passwords in
  shell history.
