# Log Miner and Logging Options

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.log.html

**Conversion category:** Manual (Three-star feature compatibility)
**SCT automation:** N/A. Key difference: PostgreSQL doesn't support LogMiner; a workaround is available.

## Oracle

Oracle Log Miner queries the Redo Logs and Archived Redo Logs via SQL, letting you analyze online/archived redo logs for historical activity (e.g. DML by individual statements).

```sql
-- find current redo log file
SELECT V$LOG.STATUS, MEMBER
FROM V$LOG, V$LOGFILE
WHERE V$LOG.GROUP# = V$LOGFILE.GROUP#
AND V$LOG.STATUS = 'CURRENT';

-- add the log file
BEGIN
DBMS_LOGMNR.ADD_LOGFILE('/u01/app/oracle/oradata/orcl/redo02.log');
END;
/

-- start Log Miner
BEGIN
DBMS_LOGMNR.START_LOGMNR(options=> dbms_logmnr.dict_from_online_catalog);
END;
/

-- run DML
UPDATE HR.EMPLOYEES SET SALARY=SALARY+1000 WHERE EMPLOYEE_ID=116;
COMMIT;

-- query captured changes (note SQL_REDO and SQL_UNDO)
SELECT TO_CHAR(TIMESTAMP,'mm/dd/yy hh24:mi:ss') TIMESTAMP,
SEG_NAME, OPERATION, SQL_REDO, SQL_UNDO
FROM V$LOGMNR_CONTENTS
WHERE TABLE_NAME = 'EMPLOYEES'
AND OPERATION = 'UPDATE';
-- SQL_REDO: update "HR"."EMPLOYEES" set "SALARY"='3900' where "SALARY"='2900' and ROWID=...
-- SQL_UNDO: update "HR"."EMPLOYEES" set "SALARY"='2900' where "SALARY"='3900' and ROWID=...
```

## PostgreSQL

PostgreSQL has no direct Log Miner equivalent, but several alternatives expose historical activity.

**1. pg_stat_statements** — extension tracking query execution with statistics (one row per logged operation: user, query, rows, timing, block I/O).

RDS setup: in the parameter group set `shared_preload_libraries = 'pg_stat_statements'`, `pg_stat_statements.max = 10000`, `pg_stat_statements.track = all` (reboot may be required), then:
```sql
CREATE EXTENSION PG_STAT_STATEMENTS;

UPDATE EMPLOYEES SET SALARY=SALARY+1000 WHERE EMPLOYEE_ID=116;

SELECT * FROM PG_STAT_STATEMENTS WHERE LOWER(QUERY) LIKE '%update%';
-- query: UPDATE EMPLOYEES SET SALARY = SALARY + ? WHERE EMPLOYEE_ID=?
-- calls, total_time, min/max/mean_time, rows, shared_blks_hit/read, etc.
```
Note: `pg_stat_statements` has **no equivalent to LogMiner's `SQL_UNDO`** column.

**2. DML/DDL activity logging** to the PostgreSQL log file (postgres.log), viewable in the AWS console. RDS parameter group: `log_statement = 'ALL'`, `log_min_duration_statement = 1` (reboot may be required). View under RDS → Databases → your DB → Logs.

**3. Amazon Aurora Performance Insights** — dashboard of current/historical SQL statements, runs, and workloads. Enable Enhanced Monitoring during/after instance configuration (RDS → Databases → Modify → Enable Enhanced Monitoring = Yes → Apply immediately), then RDS → Performance Insights → choose instance → set timeframe and scope (Waits, SQL, Hosts, Users).

## Conversion notes
- **No LogMiner** in PostgreSQL — there is no built-in way to read redo/WAL as SQL with redo/undo reconstruction.
- Closest alternatives: `pg_stat_statements` (query stats), server log statement logging (`log_statement='ALL'`), and Aurora **Performance Insights**.
- Critical gap: no `SQL_UNDO` equivalent — you cannot auto-generate compensating/undo statements as Oracle Log Miner does.
- For change-data-capture needs (rather than auditing), use logical replication / AWS DMS instead.
