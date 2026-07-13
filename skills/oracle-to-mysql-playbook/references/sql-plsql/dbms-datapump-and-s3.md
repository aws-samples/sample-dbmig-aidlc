# DBMS_DATAPUMP and S3 Integration

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.datapump.html

**Conversion category:** Manual (★ feature compatibility, no automation)
**SCT automation:** N/A — no equivalent tool.

## Oracle

`DBMS_DATAPUMP` runs Oracle Data Pump within the database to transfer data objects between databases or export to OS files. Subprograms: `ADD_FILE`, `ATTACH`, `DATA_FILTER`, `DETACH`, `GET_DUMPFILE_INFO`, `GET_STATUS`, `LOG_ENTRY`, `METADATA_FILTER`, `METADATA_REMAP`, `METADATA_TRANSFORM`, `OPEN`, `SET_PARALLEL`, `SET_PARAMETER`, `START_JOB`, `STOP_JOB`, `WAIT_FOR_JOB`.

```sql
-- Export the HR schema (directories/privileges assumed to exist)
DECLARE
  loopidx NUMBER;
  job_handle NUMBER;
  percent_done NUMBER;
  job_state VARCHAR2(30);
  err ku$_LogEntry;
  job_status ku$_JobStatus;
  job_desc ku$_JobDesc;
  obj_stat ku$_Status;
BEGIN
  job_handle := DBMS_DATAPUMP.OPEN('EXPORT','SCHEMA',NULL,'EXP_SAMP','LATEST');
  DBMS_DATAPUMP.ADD_FILE(job_handle,'hr.dmp','DMPDIR');
  DBMS_DATAPUMP.METADATA_FILTER(job_handle,'SCHEMA_EXPR','IN (''HR'')');
  DBMS_DATAPUMP.START_JOB(job_handle);
  percent_done := 0;
  job_state := 'UNDEFINED';
  while (job_state != 'COMPLETED') and (job_state != 'STOPPED') loop
    dbms_datapump.get_status(job_handle,
      dbms_datapump.ku$_status_job_error +
      dbms_datapump.ku$_status_job_status +
      dbms_datapump.ku$_status_wip,-1,job_state,obj_stat);
    job_status := obj_stat.job_status;
    if job_status.percent_done != percent_done then
      percent_done := job_status.percent_done;
    end if;
    -- error handling over obj_stat.mask / err ...
  end loop;
  dbms_datapump.detach(job_handle);
END;
/
```

## MySQL

No fully equivalent feature. Use Aurora MySQL ↔ Amazon S3 integration:
* **Export to S3:** `SELECT INTO OUTFILE S3`
* **Import from S3:** `LOAD DATA FROM S3`

Combine with metadata tables and events to orchestrate operations. See "Oracle External Tables and MySQL Integration with Amazon S3".

## Conversion notes

| Oracle DBMS_DATAPUMP | Aurora + S3 |
|---|---|
| `ADD_FILE` | Use metadata table |
| `ATTACH` | Query session status |
| `DATA_FILTER` | `WHERE` clause in `SELECT` |
| `DETACH` | Not required |
| `GET_DUMPFILE_INFO` | Use metadata table |
| `GET_STATUS` | Query session status |
| `LOG_ENTRY` | Write to metadata tables |
| `METADATA_FILTER` | Export the objects |
| `METADATA_REMAP` | `LOAD DATA INTO` a different table name |
| `METADATA_TRANSFORM` | Not required |
| `OPEN` | `LOAD DATA` or `SAVE OUTFILE` |
| `SET_PARALLEL` | Use parallelism in `SELECT` |
| `SET_PARAMETER` | Not required |
| `START_JOB` | `LOAD DATA` or `SAVE OUTFILE` |
| `STOP_JOB` | Kill session |
| `WAIT_FOR_JOB` | `LOAD DATA` or `SAVE OUTFILE` |

- Requires configuring the Aurora MySQL cluster with an IAM role granting S3 access.
- For full database/schema migration, prefer AWS DMS + AWS SCT rather than reimplementing Data Pump.
