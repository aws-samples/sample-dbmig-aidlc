# Export and import features

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.exportimport.html

**Conversion category:** N/A (no feature compatibility — non-compatible tool)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PG 16–18 `pg_dump` options, client-side `\copy` (server file COPY unsupported, verified), PG 17/18 `ON_ERROR`/`REJECT_LIMIT`, fixed S3 pipe and restore examples, BCP mapping, DMS 3.5.4+.

## SQL Server

SQL Server provides many options for exporting/importing text files for data migration, scripting, and backup:
- Save results to a file in SSMS.
- SQLCMD command-line utility.
- PowerShell wrapper for SQLCMD.
- SSMS Import/Export Wizard.
- SQL Server Reporting Services (SSRS).
- Bulk Copy Program (BCP).

SQLCMD runs T-SQL statements, system procedures, and script files over ODBC. Example:

```text
SQLCMD -i C:\sql\myquery.sql -o C:\sql\output.txt
```

Common SQLCMD options include: `-S server`, `-d db_name`, `-U login` / `-P password` / `-E` (trusted), `-i input_file`, `-o output_file`, `-Q "query"` (and exit), `-s col_separator`, `-W` (trim trailing spaces), `-h rows_per_header`.

Example — connect to a named instance with Windows Authentication and specify input/output files:

```text
sqlcmd -S MyMSSQLServer\MyMSSQLInstance -i query.sql -o outputfile.txt
```

For import to another database, query the data as `INSERT` commands and `CREATE` for the object. You can export with SQLCMD and import with the Export/Import wizard.

## PostgreSQL

PostgreSQL provides `pg_dump` and `pg_restore` for logical export/import (comparable to SQLCMD use for moving data and creating logical backups). Binaries must be installed locally or on an Amazon EC2 server as part of the PostgreSQL client.

Dump files can be copied to Amazon S3 for cloud backup/retention, then copied back to a client and restored with `pg_restore`.

Current `pg_dump`/`pg_restore` capabilities (use **PostgreSQL 18 client binaries** against Aurora PostgreSQL 18):
- Schema/table include and exclude (`-n`/`-N`, `-t`/`-T`), or a filter file with `--filter=file` (PG 17+).
- Compression `-Z gzip|lz4|zstd[:level]` (PG 16+).
- Parallel dump/restore with the directory format (`-Fd -j N`).
- Optimizer statistics with `--statistics` / `--statistics-only` (PG 18; off by default).
- `pg_dumpall --no-role-passwords` (required on Aurora, where the master user cannot read `pg_authid`).

Notes:
- `pg_dump` creates consistent backups even under concurrent use and does not block readers/writers.
- `pg_dump` exports a single database; use `pg_dumpall` for cluster-global objects (roles, tablespaces).
- Dump files can be plain-text or custom format.
- Dump files can be plain-text (restore with `psql -f`) or custom/directory (restore with `pg_restore`).
- `COPY TO` / `COPY FROM` is the BCP equivalent, run **client-side** on Aurora. Server-side file `COPY` is not supported (verified on 18.6). Use `psql \copy`, `COPY … FROM STDIN` in a driver, or `aws_s3.table_import_from_s3` / `query_export_to_s3`. Row filtering with `WHERE` (PG 12+) and error tolerance `ON_ERROR ignore` (PG 17), `REJECT_LIMIT n` (PG 18), similar to BCP `-m max_errors`, are available. They are community features; test them with `\copy`:

  ```sql
  CREATE TABLE tst_copy(v TEXT);
  \copy tst_copy FROM 'file.csv' WITH (FORMAT CSV, ON_ERROR ignore, REJECT_LIMIT 100) WHERE v LIKE '%apple%'
  ```

Examples:

```bash
# Export with pg_dump (custom format, zstd)
pg_dump -Fc -Z zstd -h hostname.rds.amazonaws.com -U username -d db_name -f db_name.dump

# Export and stream to S3 via pipe + AWS CLI (stdout: no -f)
pg_dump -Fc -h hostname.rds.amazonaws.com -U username -d db_name \
  | aws s3 cp - s3://<your-unique-bucket-name>/pg_bck-$(date "+%Y-%m-%d-%H-%M-%S").dump

# Restore a custom-format dump with pg_restore (plain .sql dumps are restored with psql -f)
pg_restore -h hostname.rds.amazonaws.com -U username -d dbname_restore db_name.dump

# BCP-style export of one query to CSV
psql -h hostname.rds.amazonaws.com -U username -d db_name \
  -c "\copy (SELECT * FROM sales WHERE year = 2024) TO 'sales_2024.csv' WITH (FORMAT csv, HEADER)"

# Copy a dump file to/from S3 (date suffix is Linux-only)
aws s3 cp /usr/Exports/hr.dmp s3://<your-unique-bucket-name>/backup-$(date "+%Y-%m-%d-%H-%M-%S")
aws s3 cp s3://<your-unique-bucket-name>/backup-2017-09-10-01-10-10 /usr/Exports/hr.dmp
```

Copy an existing database without `pg_dump`/`pg_restore` using a template (no other sessions connected to the source; for a whole-cluster copy, an Aurora fast clone is faster):

```sql
CREATE DATABASE mydb_copy TEMPLATE mydb;
```

### Summary

| Description | SQL Server | PostgreSQL |
|---|---|---|
| Export data to a file | `SQLCMD -i C:\sql\myquery.sql -o C:\sql\output.txt` or Export/Import Wizard | `pg_dump -F c -h hostname.rds.amazonaws.com -U username -d hr -p 5432 > c:\Export\hr.dmp` |
| Import data to a new database | Run SQLCMD with objects + data creation script: `SQLCMD -i C:\sql\myquery.sql` | `pg_restore` of the dump file |

## Conversion notes

- Non-compatible tooling — SQLCMD/BCP/SSMS wizard have no direct equivalent; use `pg_dump`/`pg_restore` (or `COPY`) instead.
- AWS integration: stage/retrieve dump files in Amazon S3 (optionally piped through the AWS CLI); run client binaries from a workstation or Amazon EC2.
- `pg_dump` is single-database; use `pg_dumpall` for cluster-wide global objects.
- For large/production data movement prefer AWS DMS over manual dump/restore. SQL Server → Aurora PostgreSQL 18 needs DMS replication engine **3.5.4+**. In this toolkit, `dbmig migrate-data` handles dev/test loads.
- `bcp out` / `bcp in` → `\copy … TO/FROM`; BCP format files have no equivalent (use column lists in `\copy`).
