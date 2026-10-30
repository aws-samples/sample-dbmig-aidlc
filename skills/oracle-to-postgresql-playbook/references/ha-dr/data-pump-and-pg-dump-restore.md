# Oracle Data Pump and PostgreSQL pg_dump and pg_restore

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.hadr.datapump.html

**Conversion category:** Manual (No compatibility — non-compatible tool; use the PostgreSQL-native equivalent)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): replaced the PG 10/11 capability list with PG 16–18 options (`--filter`, zstd, `--statistics`), noted that server-side file `COPY` is unavailable on Aurora, and fixed the S3 streaming and plain-text restore examples.

## Oracle

Oracle Data Pump exports and imports data from/to an Oracle database. It can copy an entire database, entire schemas, or specific objects, and is commonly used to restore individual database objects (records, tables, views, stored procedures) — as opposed to snapshots or RMAN, which work at the database level. By default (without the `sqlfile` parameter on export) the dump file is **binary** (not text-editable). A dump file created by Data Pump is referred to as a "logical backup."

Data Pump supports:
- **Export** (`EXPDP`) — creates a binary dump file of exported objects. Objects can be exported with data or metadata only. Exports can target specific timestamps or SCNs for cross-object consistency.
- **Import** (`IMPDP`) — imports objects/data from a dump file created by `EXPDP`. Can filter on import (only certain objects) and remap object/schema names.

Both `EXPDP` and `IMPDP` read/write dump files only from file system paths pre-configured in the database as **directories**. Users specify the logical directory name (not the physical path).

Examples:

```bash
# Export the HR schema
$ expdp system directory=expdp_dir schemas=hr dumpfile=hr.dmp logfile=hr.log

# Import the HR schema and rename to HR_COPY
$ impdp system directory=expdp_dir schemas=hr dumpfile=hr.dmp logfile=hr.log REMAP_SCHEMA=hr:hr_copy
```

See: [Oracle Data Pump](https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/oracle-data-pump.html).

> **Credentials:** never embed a password in a Data Pump command (it leaks into shell history,
> process lists, and logs). Invoking `expdp`/`impdp` with just the username (e.g. `expdp system`)
> prompts for the password interactively; for automation use an Oracle Wallet / external password
> store. Likewise, `pg_dump`/`pg_restore` should read the password from `~/.pgpass` or the
> `PGPASSWORD`/AWS Secrets Manager env, not an inline argument.

## PostgreSQL

PostgreSQL provides native utilities `pg_dump` and `pg_restore` with comparable functionality to Oracle Data Pump (moving data between databases and creating logical backups):
- `pg_dump` ≈ Oracle `expdp`
- `pg_restore` ≈ Oracle `impdp`

Aurora PostgreSQL supports both, but the binaries must be placed on your local workstation or an EC2 server as part of the PostgreSQL client binaries. Dump files can be copied to Amazon S3 for cloud backup/retention, then copied back to a host with a PostgreSQL client for `pg_restore`.

Capabilities in current `pg_dump`/`pg_restore` (use client binaries of the **same or newer major version** as the server, i.e. PostgreSQL 18 client tools for Aurora PostgreSQL 18):
- Exclude a schema (`-N`) or table (`-T`), or list include/exclude patterns in a file with `--filter=file` (PG 17+), which is the closest equivalent to an expdp parameter file with `INCLUDE`/`EXCLUDE`.
- Compression with `-Z gzip|lz4|zstd[:level]` (PG 16+). `zstd` is usually faster and smaller than the default gzip.
- Parallel dump and restore with the directory format: `pg_dump -Fd -j 8` / `pg_restore -j 8`, the equivalent of expdp `PARALLEL`.
- Optimizer statistics with `--statistics` (off by default) or `--statistics-only` (PG 18). Restoring statistics avoids a long `ANALYZE` before the first queries.
- Run `pg_dumpall` by non-superusers using `--no-role-passwords` (required on Aurora, where the master user cannot read `pg_authid`).
- `pg_dump` and `pg_restore` export/import extension–object dependencies (`ALTER … DEPENDS ON EXTENSION`).

Notes:
- `pg_dump` creates consistent backups even under concurrent use and does not block readers or writers.
- `pg_dump` only exports a **single database**; use `pg_dumpall` to back up global objects common to a cluster (roles, tablespaces).
- Dump files can be plain-text (restore with `psql -f`) or custom/directory/tar format (restore with `pg_restore`). `pg_restore` cannot read a plain-text dump.
- Alternative: `COPY TO` / `COPY FROM`. **On Aurora, server-side file `COPY` is not available** (verified on 18.6: `COPY from a file is not supported`). Use client-side `psql \copy`, `COPY … FROM STDIN` from a driver, or `aws_s3.table_import_from_s3` / `aws_s3.query_export_to_s3`. `COPY FROM` row filtering with `WHERE` (PG 12+) works with STDIN:

```sql
CREATE TABLE tst_copy(v TEXT);
\copy tst_copy FROM 'file.csv' WITH (FORMAT CSV) WHERE v LIKE '%apple%'
```

- PostgreSQL 17/18 add `COPY FROM` error tolerance, comparable to impdp/SQL*Loader bad-record handling: `ON_ERROR ignore` skips rows with malformed values, `REJECT_LIMIT n` (PG 18) aborts after `n` bad rows, and `LOG_VERBOSITY verbose` logs each skipped row. These are community PostgreSQL options; the Data API used for validation cannot run `COPY`, so test them with `psql \copy` before relying on them.

Examples:

```bash
# Export with pg_dump (custom format, zstd compression)
$ pg_dump -Fc -Z zstd -h hostname.rds.amazonaws.com -U username -d db_name -f db_name.dump

# Export and stream straight to S3 via pipe + AWS CLI (write to stdout: no -f)
$ pg_dump -Fc -h hostname.rds.amazonaws.com -U username -d db_name | aws s3 cp - s3://<your-unique-bucket-name>/pg_bck-$(date "+%Y-%m-%d-%H-%M-%S").dump

# Parallel export/restore (directory format)
$ pg_dump -Fd -j 8 -h hostname.rds.amazonaws.com -U username -d db_name -f db_name.dir
$ pg_restore -j 8 -h hostname.rds.amazonaws.com -U username -d dbname_restore db_name.dir

# Restore a custom-format dump
$ pg_restore -h hostname.rds.amazonaws.com -U username -d dbname_restore db_name.dump

# Upload a dump file to S3 (Linux date format only)
$ aws s3 cp /usr/Exports/hr.dmp s3://<your-unique-bucket-name>/backup-$(date "+%Y-%m-%d-%H-%M-%S")

# Download a dump file from S3
$ aws s3 cp s3://<your-unique-bucket-name>/backup-2017-09-10-01-10-10 /usr/Exports/hr.dmp
```

Copy an existing database without `pg_dump`/`pg_restore` using a template (no other sessions may be connected to `mydb`):

```sql
CREATE DATABASE mydb_copy TEMPLATE mydb;
```

To copy a whole Aurora cluster for test or QA, an **Aurora fast clone** (`restore-db-cluster-to-point-in-time --restore-type copy-on-write`) is faster than any logical dump.

## Conversion notes

Side-by-side mapping:

| Task | Oracle Data Pump | PostgreSQL |
|---|---|---|
| Export to local file | `expdp system schemas=hr dumpfile=hr.dmp logfile=hr.log` | `pg_dump -F c -h hostname.rds.amazonaws.com -U username -d hr -p 5432 > c:\Export\hr.dmp` |
| Export to remote file | Create Oracle directory `EXP_DIR`, then `expdp system schemas=hr directory=EXP_DIR dumpfile=hr.dmp logfile=hr.log` | `pg_dump -F c ... > c:\Export\hr.dmp` then `aws s3 cp c:\Export\hr.dmp s3://<your-unique-bucket-name>/backup-$(date"+%Y-%m-%d-%H-%M-%S")` |
| Import to a new DB with new name | `impdp system schemas=hr dumpfile=hr.dmp logfile=hr.log REMAP_SCHEMA=hr:hr_copy TRANSFORM=OID:N` | `pg_restore -h hostname.rds.amazonaws.com -U hr -d hr_restore -p 5432 c:\Export\hr.dmp` |
| Exclude schemas | `expdp system FULL=Y directory=EXP_DIR dumpfile=hr.dmp logfile=hr.log exclude=SCHEMA:"HR"` | `pg_dump -F c -h hostname.rds.amazonaws.com -U username -d hr -p 5432 -N 'log_schema' -f c:\Export\hr_nolog.dmp` |

- The tools are not compatible — this is a manual reimplementation using native PostgreSQL utilities, not an automated conversion.
- Oracle requires a pre-configured logical directory for dump file I/O; PostgreSQL writes to the local filesystem of the client host (then optionally to S3).
- Use `pg_dumpall` (not `pg_dump`) for cluster-wide global objects (roles, tablespaces).
- `-N` excludes a schema in `pg_dump`. `REMAP_SCHEMA` in `impdp` has no direct flag: restore, then `ALTER SCHEMA hr RENAME TO hr_copy;`, or restore into a differently named target database.
- Oracle-to-PostgreSQL data movement itself is not a Data Pump task. Use AWS DMS (full load + CDC), or the toolkit's `dbmig migrate-data` for dev/test.
