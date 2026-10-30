# DBMS_SCHEDULER and PostgreSQL Scheduled Lambda

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.scheduler.html

**Conversion category:** Manual (One-star feature compatibility, no automation)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): `pg_cron` is the recommended in-database scheduler (verified on 18.6, including the `schedule_in_database` restriction and its workaround); EventBridge Scheduler/Step Functions for external jobs and chains.

## Oracle

The `DBMS_SCHEDULER` package defines and runs recurring or one-time jobs. A job typically uses two objects: a `PROGRAM` (what runs) and a `SCHEDULE` (when it runs). A program can run a database program unit (e.g. a procedure) or an external executable (filesystem shell scripts, etc.). Three job types: **Time-Based**, **Event-Based**, and **Dependency (Chained)**.

**Time-based scheduling** — program + schedule + job:
```sql
BEGIN
DBMS_SCHEDULER.CREATE_PROGRAM(
program_name => 'CALC_STATS',
program_action => 'HR.UPDATE_HR_SCHEMA_STATS',
program_type => 'STORED_PROCEDURE',
enabled => TRUE);
END;
/

BEGIN
DBMS_SCHEDULER.CREATE_SCHEDULE(
schedule_name => 'stats_schedule',
start_date => SYSTIMESTAMP,
repeat_interval => 'FREQ=HOURLY;INTERVAL=1',
comments => 'Every hour');
END;
/

BEGIN
DBMS_SCHEDULER.CREATE_JOB (
job_name => 'my_new_job3',
program_name => 'my_saved_program1',
schedule_name => 'my_saved_schedule1');
END;
/
```

Create a job directly (external executable, no separate program/schedule):
```sql
BEGIN
DBMS_SCHEDULER.CREATE_JOB(
job_name=>'HR. BACKUP',
job_type => 'EXECUTABLE',
job_action => '/home/usr/dba/rman/nightly_bck.sh',
start_date=> SYSDATE,
repeat_interval=>'FREQ=DAILY;BYHOUR=23',
comments => 'Nightly backups');
END;
/
```

Update a job attribute:
```sql
BEGIN
DBMS_SCHEDULER.SET_ATTRIBUTE (
name => 'my_emp_job1',
attribute => 'repeat_interval',
value => 'FREQ=DAILY');
END;
/
```

**Event-based jobs:**
```sql
BEGIN
DBMS_SCHEDULER.CREATE_EVENT_SCHEDULE (
schedule_name => 'scott.file_arrival',
start_date => systimestamp,
event_condition => 'tab.user_data.object_owner = ''SCOTT''
and tab.user_data.event_name = ''FILE_ARRIVAL''
and extract hour from tab.user_data.event_timestamp < 9',
queue_spec => 'my_events_q');
END;
/

BEGIN
DBMS_SCHEDULER.CREATE_JOB (
job_name => my_job,
program_name => my_program,
start_date => '15-JUL-04 1.00.00AM US/Pacific',
event_condition => 'tab.user_data.event_name = ''LOW_INVENTORY''',
queue_spec => 'my_events_q'
enabled => TRUE,
comments => 'my event-based job');
END;
/
```

**Dependency (chained) jobs** — CREATE_CHAIN, DEFINE_CHAIN_STEP, DEFINE_CHAIN_RULE, ENABLE, then CREATE_JOB:
```sql
BEGIN
DBMS_SCHEDULER.CREATE_CHAIN (
chain_name => 'my_chain1',
rule_set_name => NULL,
evaluation_interval => NULL,
comments => NULL);
END;
/

BEGIN
DBMS_SCHEDULER.DEFINE_CHAIN_STEP('my_chain1', 'stepA', 'my_program1');
DBMS_SCHEDULER.DEFINE_CHAIN_STEP('my_chain1', 'stepB', 'my_program2');
DBMS_SCHEDULER.DEFINE_CHAIN_STEP('my_chain1', 'stepC', 'my_program3');
END;
/

BEGIN
DBMS_SCHEDULER.DEFINE_CHAIN_RULE ('my_chain1', 'TRUE', 'START stepA');
DBMS_SCHEDULER.DEFINE_CHAIN_RULE (
'my_chain1', 'stepA COMPLETED', 'Start stepB, stepC');
DBMS_SCHEDULER.DEFINE_CHAIN_RULE (
'my_chain1', 'stepB COMPLETED AND stepC COMPLETED', 'END');
END;
/

BEGIN
DBMS_SCHEDULER.ENABLE('my_chain1');
END;
/

BEGIN
DBMS_SCHEDULER.CREATE_JOB (
job_name => 'chain_job_1',
job_type => 'CHAIN',
job_action => 'my_chain1',
repeat_interval => 'freq=daily;byhour=13;byminute=0;bysecond=0',
enabled => TRUE);
END;
/
```

Additional maintenance concepts: **JOB CLASS** (group jobs with similar behavior, assign resource priority) and **WINDOW** (time window for prioritizing jobs, e.g. off-peak or month-end).

## PostgreSQL

Aurora PostgreSQL has no built-in DBMS_SCHEDULER equivalent. There are two supported patterns:

**1. `pg_cron` (in-database jobs; recommended for jobs that only run SQL or procedures).** `pg_cron` 1.6 is available on Aurora 18. Add it to `shared_preload_libraries` in the cluster parameter group, reboot, then (verified on 18.6):
```sql
-- the extension lives in the database named by cron.database_name (default: postgres)
CREATE EXTENSION pg_cron;                                   -- in database postgres

-- ≈ CREATE_JOB with repeat_interval 'FREQ=HOURLY;INTERVAL=1'
SELECT cron.schedule('calc_stats', '0 * * * *', $$CALL hr.update_hr_schema_stats()$$);

-- run in another database: on Aurora the master user cannot call cron.schedule_in_database
-- (permission denied, verified); schedule, then set the target database:
UPDATE cron.job SET database = 'appdb' WHERE jobname = 'calc_stats';

SELECT * FROM cron.job;                                    -- ≈ DBA_SCHEDULER_JOBS
SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 20;  -- ≈ DBA_SCHEDULER_JOB_RUN_DETAILS
SELECT cron.unschedule('calc_stats');                      -- ≈ DROP_JOB
```
Schedules use cron syntax (minute granularity, or `'30 seconds'` intervals) in UTC. Jobs run as the user who scheduled them. Purge `cron.job_run_details` periodically.

**2. Amazon EventBridge Scheduler → AWS Lambda / Step Functions (external jobs).** Use this for `EXECUTABLE` jobs (shell scripts), event-based jobs, chains, and anything that calls outside the database. Step Functions replaces `DBMS_SCHEDULER` **chains** (steps, rules, parallel branches, retries). EventBridge rules replace **event-based** jobs (S3 object created, SQS message). See the playbook topic "Sending an Email from Aurora PostgreSQL using Lambda Integration".

## Conversion notes
- No automation and lowest feature compatibility (one star) — scheduling must be re-architected.
- **Default:** time-based jobs that run a stored procedure → `pg_cron` calling the converted procedure with `CALL`. Translate `repeat_interval` to cron syntax (`FREQ=DAILY;BYHOUR=23` → `0 23 * * *`), and convert time zones to UTC.
- `EXECUTABLE` jobs, chains, event-based jobs, job classes/windows → EventBridge Scheduler + Lambda / Step Functions (Lambda connects to Aurora through RDS Proxy or the Data API).
- `pg_cron` has no job classes, windows, chains, retry policies or resource priorities. Keep complex orchestration outside the database.
- Calling AWS from SQL (for example a job that notifies a service): `aws_lambda.invoke()` (aws_lambda 2.1 on Aurora 18) with an IAM role attached to the cluster.
- Oracle `DBMS_JOB` (legacy) maps the same way as `DBMS_SCHEDULER` time-based jobs.
