# DBMS_SCHEDULER and PostgreSQL Scheduled Lambda

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.scheduler.html

**Conversion category:** Manual (One-star feature compatibility, no automation)
**SCT automation:** N/A

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

Aurora PostgreSQL has no built-in DBMS_SCHEDULER equivalent. Combine Aurora PostgreSQL with **Amazon CloudWatch** and **AWS Lambda** to achieve similar scheduled functionality (e.g. invoking a Lambda on a CloudWatch schedule). See the playbook topic "Sending an Email from Aurora PostgreSQL using Lambda Integration".

## Conversion notes
- No automation and lowest feature compatibility (one star) — scheduling must be re-architected.
- Recommended pattern: schedule with **Amazon CloudWatch Events/EventBridge → AWS Lambda**, where Lambda connects to Aurora and runs the desired SQL/procedure.
- Alternative community option (not in playbook) is the `pg_cron` extension; the playbook only documents the CloudWatch + Lambda approach.
- Map Oracle constructs: PROGRAM/SCHEDULE/JOB and chains have no direct Aurora analog and must be expressed as Lambda logic and event rules.
