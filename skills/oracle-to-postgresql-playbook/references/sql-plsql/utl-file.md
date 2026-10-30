# UTL_FILE

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.utl.html

**Conversion category:** Blocked (No feature compatibility, no automation; PostgreSQL has no `UTL_FILE` equivalent)
**SCT automation:** No automation; SCT action code index N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): orafce `utl_file` exists but is denied on Aurora (verified), so the topic stays Blocked; `aws_s3` export and Lambda patterns.

## Oracle

The `UTL_FILE` PL/SQL package reads/writes OS files outside the database (server file system or connected storage). Key procedures: `FOPEN`, `GET_LINE`, `PUT_LINE`, `FCLOSE`. `FOPEN` takes a logical Oracle directory object, file name, and access mode (`'R'` read, `'W'` write, `'A'` append). `UTL_FILE.FILE_TYPE` is the file handle type.

```sql
DECLARE
  strString1 VARCHAR2(32767);
  fileFile1 UTL_FILE.FILE_TYPE;
BEGIN
  fileFile1 := UTL_FILE.FOPEN('FILES_DIR','File1.tmp','R');
  UTL_FILE.GET_LINE(fileFile1, strString1);
  UTL_FILE.FCLOSE(fileFile1);
  fileFile1 := UTL_FILE.FOPEN('FILES_DIR','File2.tmp','A');
  utl_file.PUT_LINE(fileFile1, strString1);
  utl_file.fclose(fileFile1);
END;
/
```

## PostgreSQL

Amazon Aurora PostgreSQL does **not** provide a directly comparable alternative to Oracle `UTL_FILE`. There is no supported in-database OS file read/write API.

orafce contains a `utl_file` package (`fopen`, `get_line`, `put_line`, `fclose`, …), but on Aurora it is not usable: the master user gets `Permission denied to utl_file functions` (verified on 18.6), and the database host file system is not accessible anyway. Do not plan a conversion around orafce `utl_file` on Aurora.

## Conversion notes

- No in-database equivalent — this is a blocked feature requiring redesign.
- Move file I/O out of the database, for example:
  - Use the application/ETL layer to read/write files.
  - Use `COPY` / `\copy` (psql) for bulk import/export to/from files.
  - For S3 integration, use the `aws_s3` extension (`aws_s3.table_import_from_s3` / `aws_s3.query_export_to_s3`) on Aurora PostgreSQL. This is the closest pattern for `UTL_FILE` **write** jobs that produce extract files: build the rows with SQL and export the query result to S3.
  - For per-line custom file formats, invoke a Lambda function (`aws_lambda.invoke`) that writes the file to S3, or move the job to AWS Glue / the application.
- File access modes `'R'`/`'W'`/`'A'` and line-oriented `GET_LINE`/`PUT_LINE` logic must be reimplemented outside the database.
