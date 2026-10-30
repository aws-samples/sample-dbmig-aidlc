# Oracle SQL*Loader and MySQL mysqlimport and LOAD DATA

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.hadr.dump.html

**Conversion category:** Manual (no feature compatibility — the tool isn't compatible; use the MySQL equivalents)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): S3 load verified on both versions, strict-mode load behavior and staging-table reject handling, SET expressions, MySQL Shell importTable, toolkit data mover.

## Oracle

SQL*Loader imports data from external flat files into database tables, with a strong parsing engine and few format limitations. It can run with or without a **control file** (control files handle more complex loads; for simple loads use SQL*Loader or SQL*Loader Express without one). Outputs include the loaded data, a log file, a bad/rejected-records file, and an optional discard file.

### Examples

Create a source table:

```
CREATE TABLE customer_0 TABLESPACE users
  AS SELECT rownum id, o.* FROM all_objects o, all_objects x
    where rownum <= 1000000;
```

Create a destination table on the target:

```
CREATE TABLE customer_1 TABLESPACE users
  AS select 0 as id, owner, object_name, created
    from all_objects where 1=2;
```

Export to a delimited flat file via SQL*Plus:

```
alter session set nls_date_format = 'YYYY/MM/DD HH24:MI:SS';
set linesize 800
HEADING OFF FEEDBACK OFF array 5000 pagesize 0
spool customer_0.out
SET MARKUP HTML PREFORMAT ON SET COLSEP ',' SELECT id,
  owner, object_name, created FROM customer_0;
spool off
```

Create a control file describing the data:

```
cat << EOF > sqlldr_1.ctl
LOAD DATA
INFILE customer_0.out
into table customer_1
APPEND
fields terminated by "," optionally enclosed by '"'
(id POSITION(01:10) INTEGER EXTERNAL,
owner POSITION(12:41) CHAR,
object_name POSITION(43:72) CHAR,
created POSITION(74:92) date "YYYY/MM/DD HH24:MI:SS")
```

Import with SQL*Loader:

```
sqlldr cust_dba@targetdb control=sqlldr_1.ctl BINDSIZE=10485760 READSIZE=10485760 ROWSS=1000
```

See [SQL*Loader](https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/oracle-sql-loader.html) in the Oracle documentation.

## MySQL

Two replacements for SQL*Loader:
- **MySQL Import (mysqlimport / `LOAD DATA`)** — uses an export file similar to a control file; good when running a tool from another server or client. `LOAD DATA` can be combined with metadata tables and EVENT objects to schedule loads.
- **Load from Amazon S3 File** — load a table-formatted file stored in Amazon S3 directly into Aurora MySQL.

See [Loading data into an Aurora MySQL DB cluster from text files in an Amazon S3 bucket](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Integrating.LoadFromS3.html) in the Aurora user guide and [mysqlimport](https://dev.mysql.com/doc/refman/5.7/en/mysqlimport.html) in the MySQL documentation.

## Conversion notes
- Tools are not compatible — SQL*Loader control files do not transfer; rewrite loads as `LOAD DATA [LOCAL] INFILE` / mysqlimport, or use Aurora's native S3 load.
- Aurora MySQL's `LOAD DATA FROM S3` is the cloud-native equivalent and avoids staging data on a client/EC2 host — preferred for large bulk loads into Aurora.
- SQL*Loader's positional/fixed-width control-file mapping (`POSITION(...)`) must be re-expressed via MySQL field/line terminators and column lists; bad/discard file handling differs (MySQL reports warnings/errors rather than separate bad/discard files).
- For ongoing cross-engine data migration, AWS DMS is the recommended path rather than flat-file tooling.
- Verified on Aurora MySQL 3.13 and 8.4.8: `LOAD DATA FROM S3 [PREFIX|MANIFEST]` is available and needs `aurora_load_from_s3_role`/`aws_default_s3_role` plus the `AWS_LOAD_S3_ACCESS` role. Server-side `LOAD DATA INFILE '/path'` is not usable on Aurora; `LOAD DATA LOCAL INFILE` needs `local_infile` on both client and server.
- Aurora's default `sql_mode` is **empty**, so `LOAD DATA` adjusts bad values (truncation, zero dates) with warnings only. With `STRICT_TRANS_TABLES` set (custom parameter group or session), a bad value aborts the whole `LOAD DATA` with an error; with `IGNORE` the row is adjusted or skipped with a warning. *(Corrected 2026-10-30: this said the default is `STRICT_TRANS_TABLES`.)* There is no bad/discard file: load into an all-`VARCHAR` staging table first, then validate and `INSERT … SELECT` the good rows, keeping rejects in an error table.
- SQL*Loader `WHEN` clauses and SQL expressions → `LOAD DATA … (col1, @raw) SET col2 = STR_TO_DATE(@raw, '%d-%m-%Y')`.
- MySQL Shell `util.importTable()` loads large delimited files in parallel chunks (closest to SQL*Loader direct path).
- This toolkit's `./dbmig migrate-data` moves dev/test data with batched `INSERT`s; for production volumes hand off to AWS DMS.
- Link updated: [mysqlimport (8.4)](https://dev.mysql.com/doc/refman/8.4/en/mysqlimport.html).
