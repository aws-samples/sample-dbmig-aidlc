# Native Client Tools (sqlplus / mysql) — informational

> Framework note (dbmig-aidlc). The `dbmig` Python package does **not** use native client
> tools. It connects with Python drivers — `oracledb` (thin mode) for Oracle and `pymysql`
> (pure Python) for MySQL/Aurora MySQL — so no `sqlplus` or `mysql` install is required.
>
> This page is **informational only**, for operators inspecting either side manually.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Client version and caching_sha2_password on 8.4 (verified), MySQL Shell dump utilities, Data API as a no-network option.

**Conversion category:** N/A (tooling)

## Oracle (source) — SQL*Plus / SQLcl (manual inspection)
- `sqlplus user/pass@//host:port/service`; `SELECT DBMS_METADATA.GET_DDL('TABLE','EMP','APP') FROM dual;`
- dbmig uses the same `DBMS_METADATA` calls through `oracledb`.

## MySQL / Aurora MySQL (target) — mysql client (manual inspection)
- `mysql -h host -P 3306 -u user -p dbname` — interactive client.
- `mysqldump` / `mysql` for manual schema/data export-import; `LOAD DATA [LOCAL] INFILE` for
  bulk loads; Aurora supports `LOAD DATA FROM S3`.
- dbmig instead applies converted DDL and bulk-loads rows via `pymysql` (batched
  `executemany` INSERT) — see `./dbmig apply-schema`, `migrate-data`.

## Conversion notes
- Connectivity, DDL apply, data load, and reconciliation all run through the Python drivers;
  no native client is part of the dbmig execution path.
- Use `sslmode: require` (or stricter) for Aurora endpoints; dbmig reads connection details
  from `connections.yaml` with `${ENV_VAR}` expansion.
- A MySQL *schema* is a *database*; the Oracle schema maps to a MySQL database.
- Use an 8.4 `mysql` client against Aurora MySQL 8.4: older clients and drivers without `caching_sha2_password` support fail for new users (8.4 `authentication_policy` = `*:caching_sha2_password`, verified). `mysqldump` is deprecated in favor of MySQL Shell dump utilities (`util.dumpSchemas`, `util.loadDump`).
- The RDS Data API (`aws rds-data execute-statement`) works on Aurora MySQL 3 and 8.4 with no network path to the cluster; this review used it for all validation.
