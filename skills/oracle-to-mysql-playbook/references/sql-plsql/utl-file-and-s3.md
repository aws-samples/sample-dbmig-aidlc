# UTL_FILE and S3 Integration

> **Prerequisite — bucket naming:** the `<your-bucket>` names in the examples below are
> placeholders. Create your own uniquely-named S3 bucket first, including your AWS account ID and
> region so the name can't be pre-registered by others — e.g.
> `aws s3 mb s3://<your-app>-<ACCOUNT_ID>-<REGION>` — and substitute it. Never use a generic or
> predictable bucket name.

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.utl.html

**Conversion category:** Manual (★★ feature compatibility, no automation)
**SCT automation:** N/A — MySQL doesn't support `UTL_FILE`; Aurora MySQL has built-in S3 integration.

## Oracle

`UTL_FILE` accesses files outside the database (OS, DB server, attached storage). Key procedures: `FOPEN`, `GET_LINE`, `PUT_LINE`, `FCLOSE`. `FOPEN` modes: `'R'` read, `'W'` write, `'A'` append.

```sql
DECLARE
  strString1 VARCHAR2(32767);
  fileFile1 UTL_FILE.FILE_TYPE;
BEGIN
  fileFile1 := UTL_FILE.FOPEN('FILES_DIR','File1.tmp','R');
  UTL_FILE.GET_LINE(fileFile1, strString1);
  UTL_FILE.FCLOSE(fileFile1);
  fileFile1 := UTL_FILE.FOPEN('FILES_DIR','File2.tmp','A');
  UTL_FILE.PUT_LINE(fileFile1, strString1);
  UTL_FILE.FCLOSE(fileFile1);
END;
/
```

## MySQL

Aurora MySQL provides similar functionality via Amazon S3 integration (requires the cluster to have S3 permissions). Two directions: save to S3 and load from S3.

### Saving to S3 — `SELECT INTO OUTFILE S3`
Queries data and writes text files directly to S3 (avoids round-trip through the client). Default file-size threshold is 6 GB (larger → multiple files). On failure, already-uploaded files remain. For > 25 GB, use multiple statements. Schema/file metadata is not uploaded.

```sql
-- Basic (cross-region)
SELECT * FROM employees INTO OUTFILE S3
  's3-us-west-2://<your-bucket>/sample_employee_data'
  FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n';

-- With manifest (same region)
SELECT * FROM employees INTO OUTFILE S3
  's3://<your-bucket>/sample_employee_data'
  FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' MANIFEST ON;

-- Overwrite existing
SELECT * FROM employees INTO OUTFILE S3
  's3-us-west-2://<your-bucket>/sample_employee_data'
  FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' OVERWRITE ON;

-- Manifest + overwrite
SELECT * FROM employees INTO OUTFILE S3
  's3://<your-bucket>/sample_employee_data'
  FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' MANIFEST ON OVERWRITE ON;
```

### Loading from S3 — `LOAD DATA FROM S3` / `LOAD XML FROM S3`
Supports any text format `LOAD DATA INFILE` supports (compressed files not supported). Each successful load records an entry in `mysql.aurora_s3_load_history`.

```sql
-- From manifest
LOAD DATA FROM S3 MANIFEST 's3-us-west-2://<your-bucket>/customer.manifest'
  INTO TABLE CUSTOMER FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n'
  (ID, FIRSTNAME, LASTNAME, EMAIL);

-- Verify loaded files
SELECT * FROM mysql.aurora_s3_load_history WHERE load_prefix = 'S3_URI';

-- Single file
LOAD DATA FROM S3 's3://<your-bucket>/customerdata.csv'
  INTO TABLE store-schema.customer-table
  FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n'
  (ID, FIRSTNAME, LASTNAME, ADDRESS, EMAIL, PHONE);

-- Prefix (multiple files)
LOAD DATA FROM S3 PREFIX 's3-us-west-2://<your-bucket>/employee_data'
  INTO TABLE employees FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n'
  (ID, FIRSTNAME, LASTNAME, EMAIL, SALARY);

-- XML
LOAD XML FROM S3 's3://<your-bucket>/data.xml'
  INTO TABLE table1 (column1, @var1)
  SET table_column2 = @var1/100;
```

`aurora_s3_load_history` fields: `load_prefix`, `file_name`, `version_number`, `bytes_loaded`, `load_timestamp`. `LOAD XML FROM S3` supports three XML formats: attributes on `<row>`, child elements of `<row>`, or `<field name='col'>` elements.

## Conversion notes
- Replace `UTL_FILE` read/write with `LOAD DATA FROM S3` / `SELECT INTO OUTFILE S3`.
- Requires an IAM role on the Aurora cluster granting S3 access, plus the `aurora_select_into_s3_role`/`aurora_load_from_s3_role` (or `aws_default_s3_role`) cluster parameters.
- No row-by-row file streaming like `GET_LINE`/`PUT_LINE` — operations are bulk/set-based. Refactor line-oriented logic into set-based loads/unloads.
- Use `MANIFEST ON` for multi-file coordination and `aurora_s3_load_history` for idempotency/auditing.
