# Oracle Data Pump and PostgreSQL pg_dump and pg_restore

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.hadr.datapump.html

**Conversion category:** Manual (No compatibility — non-compatible tool; use the PostgreSQL-native equivalent)
**SCT automation:** N/A

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

Capabilities added in PostgreSQL 10:
- Exclude a schema in `pg_dump`/`pg_restore`.
- Create dumps with no blobs.
- Run `pg_dumpall` by non-superusers using `--no-role-passwords`.
- Additional integrity option to ensure data is stored to disk via `fsync()`.

PostgreSQL 11: `pg_dump` and `pg_restore` can export/import relationships between extensions and objects established with `ALTER … DEPENDS ON EXTENSION`, allowing those objects to be dropped when the extension is dropped with `CASCADE`.

Notes:
- `pg_dump` creates consistent backups even under concurrent use and does not block readers or writers.
- `pg_dump` only exports a **single database**; use `pg_dumpall` to back up global objects common to a cluster (roles, tablespaces).
- Dump files can be plain-text or custom format.
- Alternative: `COPY TO` / `COPY FROM`. From PostgreSQL 12, `COPY FROM` supports filtering incoming rows with a `WHERE` condition:

```sql
CREATE TABLE tst_copy(v TEXT);
COPY tst_copy FROM '/home/postgres/file.csv' WITH (FORMAT CSV) WHERE v LIKE '%apple%';
```

Examples:

```bash
# Export with pg_dump
$ pg_dump -h hostname.rds.amazonaws.com -U username -d db_name -f dump_file_name.sql

# Export and stream straight to S3 via pipe + AWS CLI
$ pg_dump -h hostname.rds.amazonaws.com -U username -d db_name -f dump_file_name.sql | aws s3 cp - s3://<your-unique-bucket-name>/pg_bck-$(date"+%Y-%m-%d-%H-%M-%S")

# Restore with pg_restore
$ pg_restore -h hostname.rds.amazonaws.com -U username -d dbname_restore dump_file_name.sql

# Upload a dump file to S3 (Linux date format only)
$ aws s3 cp /usr/Exports/hr.dmp s3://<your-unique-bucket-name>/backup-$(date "+%Y-%m-%d-%H-%M-%S")

# Download a dump file from S3
$ aws s3 cp s3://<your-unique-bucket-name>/backup-2017-09-10-01-10-10 /usr/Exports/hr.dmp
```

Copy an existing database without `pg_dump`/`pg_restore` using a template:

```sql
CREATE DATABASE mydb_copy TEMPLATE mydb;
```

## Conversion notes

Side-by-side mapping:

| Task | Oracle Data Pump | PostgreSQL |
|---|---|---|
| Export to local file | `expdp system schemas=hr dumpfile=hr.dmp logfile=hr.log` | `pg_dump -F c -h hostname.rds.amazonaws.com -U username -d hr -p 5432 > c:\Export\hr.dmp` |
| Export to remote file | Create Oracle directory `EXP_DIR`, then `expdp system schemas=hr directory=EXP_DIR dumpfile=hr.dmp logfile=hr.log` | `pg_dump -F c ... > c:\Export\hr.dmp` then `aws s3 cp c:\Export\hr.dmp s3://<your-unique-bucket-name>/backup-$(date"+%Y-%m-%d-%H-%M-%S")` |
| Import to a new DB with new name | `impdp system schemas=hr dumpfile=hr.dmp logfile=hr.log REMAP_SCHEMA=hr:hr_copy TRANSFORM=OID:N` | `pg_restore -h hostname.rds.amazonaws.com -U hr -d hr_restore -p 5432 c:\Export\hr.dmp` |
| Exclude schemas | `expdp system FULL=Y directory=EXP_DIR dumpfile=hr.dmp logfile=hr.log exclude=SCHEMA:"HR"` | `pg_dump -F c -h hostname.rds.amazonaws.com -U username -d hr -p 5432 -N 'log_schema' c:\Export\hr_nolog.dmp` |

- The tools are not compatible — this is a manual reimplementation using native PostgreSQL utilities, not an automated conversion.
- Oracle requires a pre-configured logical directory for dump file I/O; PostgreSQL writes to the local filesystem of the client host (then optionally to S3).
- Use `pg_dumpall` (not `pg_dump`) for cluster-wide global objects (roles, tablespaces).
- `-N` excludes a schema in `pg_dump`; `REMAP_SCHEMA` in `impdp` has no direct flag — restore into a differently named target database instead.
