# Oracle Data Pump and MySQL mysqldump and mysql

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.hadr.datapump.html

**Conversion category:** Manual (no feature compatibility — non-compatible tool; use the MySQL equivalent utilities)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Fixed the broken S3 pipe example, scoped --column-statistics=0 to 5.7 sources, MySQL Shell dump utilities, routines/events flags, REMAP_SCHEMA, DEFINER caveat, 8.4 doc links.

## Oracle

Oracle Data Pump exports/imports data and metadata from/to an Oracle database — an entire database, schemas, or specific objects. It is commonly used for object-level restore (records, tables, views, procedures) as opposed to RMAN/snapshots (database-level). By default (without the `sqlfile` parameter), the dump file is **binary**. A dump file created by Data Pump is called a *logical backup*.

- `EXPDP` — creates a binary dump containing exported objects (with data or metadata only); can export at a specific timestamp/SCN for cross-object consistency.
- `IMPDP` — imports objects/data from an `EXPDP` dump; can filter objects and remap object/schema names.

`EXPDP`/`IMPDP` read/write dump files only from filesystem paths pre-configured as Oracle **directories**; users specify the logical directory name, not the physical path.

### Examples

Export the `HR` schema:

```
$ expdp system directory=expdp_dir schemas=hr dumpfile=hr.dmp logfile=hr.log
```

Import and rename `HR` to `HR_COPY`:

```
$ impdp system directory=expdp_dir schemas=hr dumpfile=hr.dmp logfile=hr.log REMAP_SCHEMA=hr:hr_copy
```

See [Oracle Data Pump](https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/oracle-data-pump.html) in the Oracle documentation.

> **Credentials:** never embed a password in a Data Pump command (it leaks into shell history,
> process lists, and logs). Invoking `expdp`/`impdp` with just the username (e.g. `expdp system`)
> prompts for the password interactively; for automation use an Oracle Wallet / external password
> store. Likewise, `mysqldump`/`mysql` should read credentials from a MySQL option file
> (`~/.my.cnf` / `--login-path`) or AWS Secrets Manager, not an inline `-p<password>` argument.

## MySQL

MySQL provides native utilities for logical export/import:
- **mysqldump** ≈ Oracle `expdp` — logical export.
- **mysql** ≈ Oracle `impdp` — runs `CREATE`/`INSERT` scripts to rebuild schema and insert data (like SQL*Plus for import).
- **mysqlimport** ≈ Oracle SQL*Loader — reads a CSV file, maps to `LOAD DATA`; use it when you have a data file (not a script) and want a fast load.

Aurora MySQL supports export/import via mysqldump, mysqlimport, or mysql creation scripts. Binaries must be installed on your workstation or an EC2 server. Dump files can be copied to/from Amazon S3.

Notes:
- mysqldump creates consistent backups **only** with `--single-transaction`.
- mysqldump does **not** block other readers/writers.
- Unlike Data Pump, mysqldump files are **plain text**.
- `--column-statistics=0` is only needed when an 8.x `mysqldump` dumps a 5.7 server (it otherwise queries histogram tables that 5.7 lacks). Against Aurora MySQL 3 / 8.4 use an 8.0/8.4 client without it.
- **MySQL Shell dump utilities** (`util.dumpSchemas()`, `util.dumpTables()`, `util.loadDump()`) are the modern equivalent of `expdp`/`impdp`: parallel, chunked, compressed, can write to and load from S3 directly, and support schema renaming on load. Prefer them over `mysqldump` for anything larger than a few GB. `mysqldump` is deprecated in MySQL 8.4.

### Examples

Export with mysqldump:

```
mysqldump --column-statistics=0 DATABASE_TO_RESTORE -h INSTANCE_ENDPOINT -P 3306 -u USER_NAME -p > /local_path/backup-file.sql
```

Export and pipe to S3 with the AWS CLI:

```
mysqldump --single-transaction DATABASE_NAME -h MYSQL_INSTANCE_ENDPOINT -P 3306 -u USER_NAME -p \
  | aws s3 cp - s3://<your-unique-bucket-name>/mysql_bck-$(date "+%Y-%m-%d-%H-%M-%S").sql
# (the original redirected to a file *and* piped, so nothing reached S3)
```

Import with mysql:

```
mysql DB_NAME -h MYSQL_INSTANCE_ENDPOINT -P 3306 -u USER_NAME -p < /local_path/backupfile.sql
```

Copy a backup file to / from S3:

```
aws s3 cp /local_path/backup-file.sql s3://<your-unique-bucket-name>/backup-$(date "+%Y-%m-%d-%H-%M-%S")
$ aws s3 cp s3://<your-unique-bucket-name>/backup-2017-09-10-01-10-10 /local_path/backup-file.sql
```

(The `$(date ...)` format is valid on Linux only.)

### Summary mapping

| Task | Oracle Data Pump | MySQL |
|---|---|---|
| Export to a local file | `expdp system schemas=hr dumpfile=hr.dmp logfile=hr.log` | `mysqldump --column-statistics=0 DATABASE_TO_RESTORE -h INSTANCE_ENDPOINT -P 3306 -u USER_NAME -p > /local_path/backup-file.sql` |
| Export to a remote file | Create Oracle directory `EXP_DIR` on remote/NFS mount, then `expdp system schemas=hr directory=EXP_DIR dumpfile=hr.dmp logfile=hr.log` | `mysqldump ... -p > /local_path/backup-file.sql \| aws s3 cp - s3://<your-unique-bucket-name>/mysql_bck-$(date "+%Y-%m-%d-%H-%M-%S")` |
| Import to a new DB with a new name | `impdp system schemas=hr dumpfile=hr.dmp logfile=hr.log REMAP_SCHEMA=hr:hr_copy TRANSFORM=OID:N` | `mysql DB_NAME -h MYSQL_INSTANCE_ENDPOINT -P 3306 -u USER_NAME -p < /local_path/backup-file.sql` |

See [mysqldump](https://dev.mysql.com/doc/refman/8.4/en/mysqldump.html), [mysqlimport](https://dev.mysql.com/doc/refman/8.4/en/mysqlimport.html), [MySQL Shell dump & load utilities](https://dev.mysql.com/doc/mysql-shell/8.4/en/mysql-shell-utilities-dump-instance-schema.html).

## Conversion notes
- Tools are not compatible — dump files cannot be moved between engines; this is for like-to-like logical backup/restore, not Oracle→MySQL data migration (use AWS DMS for cross-engine data movement).
- Oracle dump files are binary and tied to Oracle directory objects; mysqldump output is plain-text SQL with no directory-object concept.
- For consistent mysqldump backups always pass `--single-transaction` (InnoDB). Add `--routines --events --triggers` to include stored code (routines and events are not dumped by default).
- `REMAP_SCHEMA` → load into another database name (`mysql other_db < dump.sql` when the dump has no `USE` statement, or `util.loadDump(…, {schema: 'hr_copy'})`).
- `DEFINER` clauses in dumps reference accounts that may not exist on the target; Aurora's master user can create them anyway (verified), but calls then fail. Recreate the accounts or strip `DEFINER` on load.
- Aurora snapshots and fast clones are faster than any logical dump for copying a whole cluster.
- `mysql` (script replay) maps to `impdp`; `mysqlimport`/`LOAD DATA` (flat-file load) maps to SQL*Loader — pick based on whether you have a SQL script or a data file.
