# Log Miner and Logging Options

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.log.html

**Conversion category:** Manual (Three-star feature compatibility)
**SCT automation:** N/A. Key difference: PostgreSQL doesn't support LogMiner; a workaround is available.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): `pg_stat_statements` preloaded by default and its column renames, `log_statement` is dynamic, `pgaudit`/Activity Streams, logical decoding and `pg_walinspect` (requires `wal_level=logical`, verified), Database Insights.

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

Aurora PostgreSQL 18 preloads `pg_stat_statements` by default (defaults: `max = 5000`, `track = top`, verified). Optionally raise `pg_stat_statements.max` (static, reboot) and set `pg_stat_statements.track = all` to include statements inside functions/procedures, then:
```sql
CREATE EXTENSION PG_STAT_STATEMENTS;

UPDATE EMPLOYEES SET SALARY=SALARY+1000 WHERE EMPLOYEE_ID=116;

SELECT * FROM PG_STAT_STATEMENTS WHERE LOWER(QUERY) LIKE '%update%';
-- query: UPDATE EMPLOYEES SET SALARY = SALARY + ? WHERE EMPLOYEE_ID=?
-- calls, total_exec_time, mean_exec_time, total_plan_time, rows, shared_blks_hit/read,
-- temp_blks_written, wal_bytes, jit_*  (columns renamed from total_time in PG 13)
```
Note: `pg_stat_statements` has **no equivalent to LogMiner's `SQL_UNDO`** column.

**2. DML/DDL activity logging** to the PostgreSQL log file (postgres.log), viewable in the AWS console. RDS parameter group: `log_statement = 'mod'` (DML+DDL) or `'all'`, `log_min_duration_statement`. Both are dynamic, so no reboot is needed. View under RDS → Databases → your DB → Logs, or export to CloudWatch Logs. For a real audit trail, use **`pgaudit`** (preload + `pgaudit.log = 'write, ddl'`) or **Database Activity Streams** (Kinesis stream, separated from DBAs).

**3. CloudWatch Database Insights** (successor to Aurora Performance Insights, which reached end of life on 2026-07-31) — dashboard of current/historical SQL statements, waits, hosts and users. Enhanced Monitoring is separate (OS metrics) and not required.

**4. Row-change capture (closest to `V$LOGMNR_CONTENTS` SQL_REDO).** Set `rds.logical_replication = 1` (cluster parameter, reboot), which sets `wal_level = logical`. Then create a logical replication slot with `test_decoding` or `wal2json` and read changes with `pg_logical_slot_get_changes()`. `pg_walinspect` (1.1) is available, but on Aurora it also requires `wal_level = logical` (verified: `wal_level must be set to 'logical'`). Drop idle slots, or set `idle_replication_slot_timeout` (PG 18), because a forgotten slot retains WAL indefinitely.

## Conversion notes
- **No LogMiner** in PostgreSQL — there is no built-in way to read redo/WAL as SQL with redo/undo reconstruction.
- Closest alternatives: `pg_stat_statements` (query stats), server log statement logging, `pgaudit`/Database Activity Streams (audit), logical decoding (row changes), and **CloudWatch Database Insights**.
- Critical gap: no `SQL_UNDO` equivalent — you cannot auto-generate compensating/undo statements as Oracle Log Miner does.
- For change-data-capture needs (rather than auditing), use logical replication / AWS DMS instead.
