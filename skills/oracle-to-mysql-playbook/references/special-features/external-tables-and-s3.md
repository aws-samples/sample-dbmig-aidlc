# Oracle External Tables and MySQL Integration with Amazon S3

> **Prerequisite — bucket naming:** the `<your-bucket>` names in the examples below are
> placeholders. Create your own uniquely-named S3 bucket first, including your AWS account ID and
> region so the name can't be pre-registered by others — e.g.
> `aws s3 mb s3://<your-app>-<ACCOUNT_ID>-<REGION>` — and substitute it. Never use a generic or
> predictable bucket name.

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.external.html

**Conversion category:** Manual (two-star feature compatibility) — use Aurora MySQL S3 integration; different paradigm and syntax.
**SCT automation:** No automation. SCT action code index: Creating Tables.

## Oracle

External tables read data from a source outside the database. Since 12.2 they can be partitioned; 18c adds inline external tables (query an external source without first defining the table).

Inline external table (18c):

```sql
SELECT * FROM EXTERNAL ((i NUMBER, d DATE)
TYPE ORACLE_LOADER
DEFAULT DIRECTORY data_dir
ACCESS PARAMETERS (
  RECORDS DELIMITED BY NEWLINE
  FIELDS TERMINATED BY '|')
LOCATION ('test.csv')
REJECT LIMIT UNLIMITED)
tst_external;
```

Create an external table with `ORGANIZATION EXTERNAL`. `TYPE` selects the driver: `ORACLE_LOADER` (text, default), `ORACLE_DATAPUMP` (binary dump, read-only after creation), `ORACLE_HDFS` (HDFS), `ORACLE_HIVE` (Apache Hive). `DEFAULT DIRECTORY`, `ACCESS PARAMETERS`, and `LOCATION` define the path, delimiters/fields, and file/URI.

```sql
CREATE TABLE emp_load
(id CHAR(5), emp_dob CHAR(20), emp_lname CHAR(30),
 emp_fname CHAR(30), emp_start_date DATE) ORGANIZATION EXTERNAL
(TYPE ORACLE_LOADER DEFAULT DIRECTORY data_dir ACCESS PARAMETERS
(RECORDS DELIMITED BY NEWLINE FIELDS (id CHAR(2), emp_dob CHAR(20),
  emp_lname CHAR(18), emp_fname CHAR(11), emp_start_date CHAR(10)
  date_format DATE mask "mm/dd/yyyy"))
LOCATION ('info.dat'));
```

## MySQL

Aurora MySQL offers similar capability via Amazon S3 integration, but there is no open/live link to files — data must be transferred in/out. Aurora MySQL must have IAM permissions to the S3 bucket. Two operations: saving to S3 and loading from S3. Inline external tables (18c) have no Aurora equivalent — consider AWS Glue for ETL.

### Saving data to Amazon S3 (`SELECT INTO OUTFILE S3`)

Default file-size threshold is 6 GB (multiple files created beyond it). If the `SELECT` fails, already-uploaded files remain (resume with another statement). For >25 GB, use multiple statements. Metadata/schema is not uploaded.

```sql
-- cross-region, comma/newline delimited
SELECT * FROM employees INTO OUTFILE S3
's3-us-west-2://<your-bucket>/sample_employee_data'
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n';

-- same region, with manifest
SELECT * FROM employees INTO OUTFILE S3
's3://<your-bucket>/sample_employee_data'
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n'
MANIFEST ON;

-- overwrite existing files
SELECT * FROM employees INTO OUTFILE S3
's3-us-west-2://<your-bucket>/sample_employee_data'
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' OVERWRITE ON;
```

### Loading data from Amazon S3 (`LOAD DATA FROM S3` / `LOAD XML FROM S3`)

Supports any text format supported by `LOAD DATA INFILE`. Compressed files are not supported. Each successful load updates `mysql.aurora_s3_load_history` (fields: `load_prefix`, `file_name`, `version_number`, `bytes_loaded`, `load_timestamp`).

```sql
-- via manifest
LOAD DATA FROM S3 MANIFEST
's3-us-west-2://<your-bucket>/customer.manifest'
INTO TABLE CUSTOMER FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
(ID, FIRSTNAME, LASTNAME, EMAIL);

-- verify loaded files
select * from mysql.aurora_s3_load_history where load_prefix = 'S3_URI';

-- single file, same region
LOAD DATA FROM S3 's3://<your-bucket>/customerdata.csv'
INTO TABLE store-schema.customer-table
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n'
(ID, FIRSTNAME, LASTNAME, ADDRESS, EMAIL, PHONE);

-- all files matching a prefix, cross-region
LOAD DATA FROM S3 PREFIX 's3-us-west-2://<your-bucket>/employee_data'
INTO TABLE employees
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n'
(ID, FIRSTNAME, LASTNAME, EMAIL, SALARY);
```

### Loading XML from S3

Three supported XML row formats: attributes of `<row>`, child elements of `<row>`, or `<field name=...>` elements. Supports `SET` with scalar subqueries (cannot select from the table being loaded).

```sql
LOAD XML FROM S3 's3://<your-bucket>/data.xml'
INTO TABLE table1 (column1, @var1)
SET table_column2 = @var1/100;

LOAD XML FROM S3 's3://<your-bucket>/data.xml'
INTO TABLE table1 (column1, column2)
SET column3 = CURRENT_TIMESTAMP;
```

## Conversion notes

- The fundamental difference: Oracle external tables are queried live in place; Aurora MySQL must physically `LOAD` the S3 data into a table (and `SELECT INTO OUTFILE S3` to export).
- No equivalent to Oracle 18c inline external tables — use AWS Glue or another ETL service.
- Compressed source files are not supported by `LOAD DATA FROM S3`.
- Aurora cluster needs an IAM role granting S3 access; manifests enable multi-file loads with load-history tracking.
