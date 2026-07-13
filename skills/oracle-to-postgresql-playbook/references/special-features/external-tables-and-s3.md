# External Tables and Amazon S3 Integration

> **Prerequisite — bucket naming:** the `<your-bucket>` names in the examples below are
> placeholders. Create your own uniquely-named S3 bucket first, including your AWS account ID and
> region so the name can't be pre-registered by others — e.g.
> `aws s3 mb s3://<your-app>-<ACCOUNT_ID>-<REGION>` — and substitute it. Never use a generic or
> predictable bucket name.

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.external.html

**Conversion category:** Manual (No feature compatibility, no automation — PostgreSQL doesn't support external tables)
**SCT automation:** No automation. SCT action code index: Creating Tables. Key difference: PostgreSQL doesn't support external tables.

## Oracle

Oracle external tables let you create a table that reads data from a source outside the database. Since 12.2 external tables can be partitioned. Oracle 18c adds **inline external tables** (read external data in a query without first defining a table):
```sql
SELECT * FROM EXTERNAL ((i NUMBER, d DATE)
TYPE ORACLE_LOADER
DEFAULT DIRECTORY data_dir
ACCESS PARAMETERS (
RECORDS DELIMITED BY NEWLINE
FIELDS TERMINATED BY '|') LOCATION ('test.csv') REJECT LIMIT UNLIMITED) tst_external;
```

Use `ORGANIZATION EXTERNAL` to declare an external table. `TYPE` chooses the driver:
- `ORACLE_LOADER` — text data files (default).
- `ORACLE_DATAPUMP` — binary dump files (write only via CREATE TABLE AS SELECT; read-only afterward, no DML).
- `ORACLE_HDFS` — data in Hadoop HDFS.
- `ORACLE_HIVE` — data in Apache Hive.
- `DEFAULT DIRECTORY` — directory path object; `ACCESS PARAMETER` — delimiter/fields; `LOCATION` — file name or URI.

```sql
CREATE TABLE emp_load
(id CHAR(5), emp_dob CHAR(20), emp_lname CHAR(30),
  emp_fname CHAR(30),emp_start_date DATE) ORGANIZATION EXTERNAL
(TYPE ORACLE_LOADER DEFAULT DIRECTORY data_dir ACCESS PARAMETERS
(RECORDS DELIMITED BY NEWLINE FIELDS (id CHAR(2), emp_dob CHAR(20),
emp_lname CHAR(18), emp_fname CHAR(11), emp_start_date CHAR(10)
date_format DATE mask "mm/dd/yyyy"))
LOCATION ('info.dat'));
```

## PostgreSQL

PostgreSQL/Aurora has no external tables. The closest capability is **Aurora PostgreSQL ↔ Amazon S3 integration**, which requires syntax changes and transfers data (no live open link to files). Two operations: **save to S3** and **load from S3**. The Aurora cluster must have IAM permissions to the S3 bucket. Oracle 18c inline external tables cannot be reproduced; for ETL consider **AWS Glue**.

**Saving data to S3** with `aws_s3.query_export_to_s3`:
```sql
CREATE EXTENSION IF NOT EXISTS aws_s3 CASCADE;

-- export to a bucket (different region)
SELECT *
FROM aws_s3.query_export_to_s3(
'SELECT * FROM employees',
aws_commons.create_s3_uri(
'<your-bucket>',
'sample_employee_data','s3-us-west-2'));

-- export as CSV with options + manifest
SELECT *
FROM aws_s3.query_export_to_s3(
'SELECT * FROM employees',
aws_commons.create_s3_uri(
'<your-bucket>',
'sample_employee_data','us-west-2'), options :='format csv, delimiter $$,$$');
```
Notes: default file-size threshold is **6 GB** (single file if under, else multiple files); failed runs leave already-uploaded files in S3 (resume rather than restart); for >25 GB use multiple runs on data portions; metadata/schema is not uploaded.

`query_export_to_s3` parameters: `query` (SQL to run), `bucket`, `file_path` (name incl. path), `region` (optional), plus `COPY` command options.

**Loading data from S3** with `aws_s3.table_import_from_s3`:
```sql
CREATE TABLE test_gzip(id int, a text, b text, c text, d text);

SELECT aws_s3.table_import_from_s3('test_gzip', '',
'(format csv)', 'myS3Bucket', 'test-data.gz', 'us-east-2');
```
`table_import_from_s3` parameters: `table_name`, `column_list` (empty = all columns), `options` (COPY args), `s3_info` (an `aws_commons._s3_uri_1` with bucket / file_path / region), `credentials` (optional; if used, you don't use an IAM role).

## Conversion notes
- PostgreSQL has **no external table** object — fundamental rewrite required.
- Replace Oracle external tables with the Aurora `aws_s3` extension (`query_export_to_s3` / `table_import_from_s3`), which physically moves data to/from S3 rather than referencing files live.
- Inline external tables (Oracle 18c) have no Aurora equivalent; use AWS Glue or other services for ETL use cases.
- Aurora cluster needs IAM permissions to the S3 bucket. The `options` strings map to PostgreSQL `COPY` parameters.
