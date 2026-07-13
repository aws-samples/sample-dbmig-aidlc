# Oracle Data Pump and MySQL mysqldump and mysql

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.hadr.datapump.html

**Conversion category:** Manual (no feature compatibility — non-compatible tool; use the MySQL equivalent utilities)
**SCT automation:** N/A

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
- In RDS for MySQL 8.0, set `--column-statistics=0` when running mysqldump from binaries.

### Examples

Export with mysqldump:

```
mysqldump --column-statistics=0 DATABASE_TO_RESTORE -h INSTANCE_ENDPOINT -P 3306 -u USER_NAME -p > /local_path/backup-file.sql
```

Export and pipe to S3 with the AWS CLI:

```
mysqldump --column-statistics=0 DATABASE_NAME -h MYSQL_INSTANCE_ENDPOINT -P 3306 -u USER_NAME -p > /local_path/backup-file.sql | aws s3 cp - s3://<your-unique-bucket-name>/mysql_bck-$(date "+%Y-%m-%d-%H-%M-%S")
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

See [mysqldump](https://dev.mysql.com/doc/refman/5.7/en/mysqldump.html), [mysqlimport](https://dev.mysql.com/doc/refman/5.7/en/mysqlimport.html), and [mysql client](https://dev.mysql.com/doc/refman/5.7/en/mysql.html).

## Conversion notes
- Tools are not compatible — dump files cannot be moved between engines; this is for like-to-like logical backup/restore, not Oracle→MySQL data migration (use AWS DMS for cross-engine data movement).
- Oracle dump files are binary and tied to Oracle directory objects; mysqldump output is plain-text SQL with no directory-object concept.
- For consistent mysqldump backups always pass `--single-transaction` (InnoDB), and `--column-statistics=0` on MySQL 8.0 client binaries.
- `mysql` (script replay) maps to `impdp`; `mysqlimport`/`LOAD DATA` (flat-file load) maps to SQL*Loader — pick based on whether you have a SQL script or a data file.
