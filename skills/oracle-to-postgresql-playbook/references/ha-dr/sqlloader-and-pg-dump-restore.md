# Oracle SQL*Loader and PostgreSQL pg_dump and pg_restore

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.hadr.dump.html

**Conversion category:** Assisted (Four-star feature compatibility, four-star automation — not all functions are supported by PostgreSQL and may require manual creation)
**SCT automation:** Four-star automation level (no specific SCT action code)

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): removed MySQL-only `LOAD DATA`/`EVENT` advice, client-side `\copy` and `aws_s3` import (server-side file COPY is not available), PG 17/18 `ON_ERROR`/`REJECT_LIMIT` for bad rows.

## Oracle

SQL*Loader imports data from external flat files into database tables. It has a strong parsing engine with few limitations on data formats. It can be used with or without a **control file** (the latter is "SQL*Loader Express", for simpler loads). Outputs include the imported data, a log file, a bad file (rejected records), and an optional discard file.

SQL*Loader suits large databases with a limited number of objects; the export/load process is very schema-specific.

Examples:

```sql
-- Create a source table
CREATE TABLE customer_0 TABLESPACE users
  AS SELECT rownum id, o.* FROM all_objects o, all_objects x
    where rownum <= 1000000;

-- On the target RDS instance, create a destination table
CREATE TABLE customer_1 TABLESPACE users
  AS select 0 as id, owner, object_name, created
    from all_objects where 1=2;
```

Export from the source to a delimited flat file (SQL*Plus):

```sql
alter session set nls_date_format = 'YYYY/MM/DD HH24:MI:SS';
set linesize 800
HEADING OFF FEEDBACK OFF array 5000 pagesize 0
spool customer_0.out
SET MARKUP HTML PREFORMAT ON SET COLSEP ',' SELECT id,
  owner, object_name, created FROM customer_0;
spool off
```

Create a control file describing the data:

```text
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

```bash
sqlldr cust_dba@targetdb control=sqlldr_1.ctl BINDSIZE=10485760 READSIZE=10485760 ROWSS=1000
```

See: [SQL*Loader](https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/oracle-sql-loader.html).

## PostgreSQL

Two options replace Oracle SQL*Loader:
- **PostgreSQL Import** using an export file similar to a control file.
- **Load from Amazon S3 File** using a table-formatted file on S3, loaded into a PostgreSQL database.

`pg_restore` applies only to `pg_dump` archives, not to flat files. To schedule recurring loads, use `pg_cron` (available on Aurora 18) to call `aws_s3.table_import_from_s3`, or an external scheduler (EventBridge Scheduler + Lambda/Step Functions/AWS Glue) that runs the load.

The main replacement for SQL*Loader is `COPY FROM`, run **client-side** on Aurora. Server-side file `COPY` is not available (verified on 18.6: `COPY from a file is not supported`).

```sql
-- client side (psql), with row filter (PG 12+)
CREATE TABLE tst_copy(v TEXT);
\copy tst_copy FROM 'file.csv' WITH (FORMAT CSV, HEADER) WHERE v LIKE '%apple%'

-- server side from S3 (aws_s3 extension, needs an IAM role attached to the cluster)
CREATE EXTENSION IF NOT EXISTS aws_s3 CASCADE;
SELECT aws_s3.table_import_from_s3('tst_copy', '', '(FORMAT csv, HEADER)',
       aws_commons.create_s3_uri('my-bucket', 'in/file.csv', 'us-west-2'));
```

SQL*Loader **bad-file / `ERRORS=`** equivalents (PostgreSQL 17/18 `COPY` options, community feature; test with `\copy`, as the Data API used for validation cannot run `COPY`):

```sql
\copy customer_1 FROM 'customer_0.csv' WITH (FORMAT csv, ON_ERROR ignore, REJECT_LIMIT 100, LOG_VERBOSITY verbose)
```

`ON_ERROR ignore` (PG 17) skips rows whose values fail type conversion. `REJECT_LIMIT` (PG 18) aborts after N rejected rows, like `ERRORS=N`. Skipped rows are reported as `NOTICE`s, not written to a bad file. Constraint violations still abort the load, so stage into a constraint-free table and `INSERT … SELECT` when you need SQL*Loader-style reject handling for constraints.

See: [PostgreSQL pg_dump and pg_restore](./data-pump-and-pg-dump-restore.md).

## Conversion notes

- Partial compatibility: not all SQL*Loader functions are supported by PostgreSQL and some may require manual reimplementation.
- Closest functional replacements for bulk flat-file loads are client-side `COPY FROM` / `\copy` (fast, native, supports CSV, `WHERE` filtering, and PG 17/18 `ON_ERROR`/`REJECT_LIMIT`) and `aws_s3.table_import_from_s3`.
- SQL*Loader control files (fixed-width `POSITION(...)`, datatype conversions, APPEND mode) have no direct equivalent — recreate the parsing/transformation logic via `COPY` options or pre-processing of the input file.
- `pg_restore` is appropriate when working from custom-format dumps rather than raw flat files; for raw delimited/fixed-width files use `COPY`.
- For scheduled/repeated loads, use `pg_cron` + `aws_s3.table_import_from_s3`, or an external scheduler. (`LOAD DATA` and `EVENT` are MySQL features, not PostgreSQL.)
- Fixed-width files: load each line into a one-column staging table, then split with `substr()` in `INSERT … SELECT`, or use `file_fdw`-style pre-processing outside the database (`file_fdw` is not available on Aurora).
