# Export and import features

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.exportimport.html

**Conversion category:** N/A (no feature compatibility — non-compatible tool)
**SCT automation:** N/A

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

Version additions:
- PostgreSQL 10: exclude a schema in `pg_dump`/`pg_restore`; dumps with no blobs; allow `pg_dumpall` by non-superusers via `--no-role-passwords`; `fsync()` integrity option.
- PostgreSQL 11: `pg_dump`/`pg_restore` export/import extension–object dependency relationships (`ALTER … DEPENDS ON EXTENSION`).

Notes:
- `pg_dump` creates consistent backups even under concurrent use and does not block readers/writers.
- `pg_dump` exports a single database; use `pg_dumpall` for cluster-global objects (roles, tablespaces).
- Dump files can be plain-text or custom format.
- `COPY TO` / `COPY FROM` is another option; since PostgreSQL 12, `COPY FROM` supports row filtering with `WHERE`:

  ```sql
  CREATE TABLE tst_copy(v TEXT);
  COPY tst_copy FROM '/home/postgres/file.csv' WITH (FORMAT CSV) WHERE v LIKE '%apple%';
  ```

Examples:

```bash
# Export with pg_dump
pg_dump -h hostname.rds.amazonaws.com -U username -d db_name -f dump_file_name.sql

# Export and stream to S3 via pipe + AWS CLI
pg_dump -h hostname.rds.amazonaws.com -U username -d db_name -f dump_file_name.sql \
  | aws s3 cp - s3://<your-unique-bucket-name>/pg_bck-$(date "+%Y-%m-%d-%H-%M-%S")

# Restore with pg_restore
pg_restore -h hostname.rds.amazonaws.com -U username -d dbname_restore dump_file_name.sql

# Copy a dump file to/from S3 (date suffix is Linux-only)
aws s3 cp /usr/Exports/hr.dmp s3://<your-unique-bucket-name>/backup-$(date "+%Y-%m-%d-%H-%M-%S")
aws s3 cp s3://<your-unique-bucket-name>/backup-2017-09-10-01-10-10 /usr/Exports/hr.dmp
```

Copy an existing database without `pg_dump`/`pg_restore` using a template:

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
- For large/production data movement prefer AWS DMS over manual dump/restore.
