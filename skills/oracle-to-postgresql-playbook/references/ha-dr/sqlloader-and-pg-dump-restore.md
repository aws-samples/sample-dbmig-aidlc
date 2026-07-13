# Oracle SQL*Loader and PostgreSQL pg_dump and pg_restore

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.hadr.dump.html

**Conversion category:** Assisted (Four-star feature compatibility, four-star automation — not all functions are supported by PostgreSQL and may require manual creation)
**SCT automation:** Four-star automation level (no specific SCT action code)

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

`pg_restore` is a good option when using a tool from another server or client. The `LOAD DATA` command can be combined with meta-data tables and `EVENT` objects to schedule loads.

Another option is the `COPY TO` / `COPY FROM` commands. From PostgreSQL 12, `COPY FROM` supports filtering incoming rows with a `WHERE` condition:

```sql
CREATE TABLE tst_copy(v TEXT);
COPY tst_copy FROM '/home/postgres/file.csv' WITH (FORMAT CSV) WHERE v LIKE '%apple%';
```

See: [PostgreSQL pg_dump and pg_restore](./data-pump-and-pg-dump-restore.md).

## Conversion notes

- Partial compatibility: not all SQL*Loader functions are supported by PostgreSQL and some may require manual reimplementation.
- Closest functional replacements for bulk flat-file loads are PostgreSQL `COPY FROM` (fast, native, supports CSV and `WHERE` filtering from v12) and loading from S3.
- SQL*Loader control files (fixed-width `POSITION(...)`, datatype conversions, APPEND mode) have no direct equivalent — recreate the parsing/transformation logic via `COPY` options or pre-processing of the input file.
- `pg_restore` is appropriate when working from custom-format dumps rather than raw flat files; for raw delimited/fixed-width files use `COPY`.
- For scheduled/repeated loads, combine `COPY`/`LOAD DATA` with metadata tables and `EVENT` scheduling.
