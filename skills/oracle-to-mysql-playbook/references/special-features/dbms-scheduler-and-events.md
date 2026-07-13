# Oracle DBMS_SCHEDULER and MySQL Events

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.scheduler.html

**Conversion category:** Manual (three-star feature compatibility) — different paradigm and syntax.
**SCT automation:** N/A

## Oracle

The `DBMS_SCHEDULER` package provides scheduling functions callable from PL/SQL. Two main objects: a **program** (what to run) and a **schedule** (when to run). Jobs can run a database program unit (procedure) or an external executable (shell script). Three job types: time-based, event-based, and dependency (chained) jobs.

Time-based scheduling — program + schedule + job:

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

Job that runs an external executable (no program/schedule), daily at 23:00:

```sql
BEGIN
  DBMS_SCHEDULER.CREATE_JOB(
    job_name=>'HR.BACKUP',
    job_type => 'EXECUTABLE',
    job_action => '/home/usr/dba/rman/nightly_bck.sh',
    start_date=> SYSDATE,
    repeat_interval=>'FREQ=DAILY;BYHOUR=23',
    comments => 'Nightly backups');
END;
/
```

Update job attributes with `SET_ATTRIBUTE`:

```sql
BEGIN
  DBMS_SCHEDULER.SET_ATTRIBUTE (
    name => 'my_emp_job1',
    attribute => 'repeat_interval',
    value => 'FREQ=DAILY');
END;
/
```

Event-based schedule + job (e.g., file arrival before 9:00):

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
```

Dependency (chained) jobs use `CREATE_CHAIN`, `DEFINE_CHAIN_STEP`, `DEFINE_CHAIN_RULE`, `ENABLE`, then a `CREATE_JOB` with `job_type => 'CHAIN'`:

```sql
BEGIN
  DBMS_SCHEDULER.CREATE_CHAIN (chain_name => 'my_chain1', rule_set_name => NULL,
    evaluation_interval => NULL, comments => NULL);
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
  DBMS_SCHEDULER.DEFINE_CHAIN_RULE ('my_chain1', 'stepA COMPLETED', 'Start stepB, stepC');
  DBMS_SCHEDULER.DEFINE_CHAIN_RULE ('my_chain1', 'stepB COMPLETED AND stepC COMPLETED', 'END');
END;
/
BEGIN DBMS_SCHEDULER.ENABLE('my_chain1'); END;
/
BEGIN
  DBMS_SCHEDULER.CREATE_JOB (job_name => 'chain_job_1', job_type => 'CHAIN',
    job_action => 'my_chain1', repeat_interval => 'freq=daily;byhour=13;byminute=0;bysecond=0',
    enabled => TRUE);
END;
/
```

Additional objects: `JOB CLASS` (group jobs with shared attributes/priority) and `WINDOW` (time window for prioritized scheduling, e.g., non-peak).

## MySQL

Aurora MySQL uses `EVENT` objects to run scheduled events (one-time or recurring/cycled). An event is a time-based trigger that runs SQL or calls a procedure. The `event_scheduler` parameter must be `ON` (not the default). Event errors are written to the error log; to emulate `dba_scheduler_job_log`, set the error log output to `TABLE`.

Check the scheduler is on:

```sql
select @@GLOBAL.event_scheduler;
```

View all events:

```sql
select * from INFORMATION_SCHEMA.EVENTS;
```

Create an event that calls a procedure every minute:

```sql
CREATE EVENT event_exec_myproc ON SCHEDULE EVERY 1 MINUTE
  DO CALL simpleproc1(5);
```

Stored-procedure equivalent of the Oracle hourly job:

```sql
CREATE EVENT stats_schedule
  ON SCHEDULE EVERY 1 HOUR
  DO CALL HR.UPDATE_HR_SCHEMA_STATS();
```

## Conversion notes

- **Stored-procedure jobs** → straightforward `CREATE EVENT ... DO CALL proc()`.
- **External executable jobs** → no OS execution in Aurora; invoke an AWS Lambda function instead:
  ```sql
  CALL mysql.lambda_async(
    'arn:aws:lambda:us-west-2:123456789012:function:oe.my_saved_program1',
    '{"input1":"value"}');
  ```
- **Event-based jobs** → `CREATE EVENT` triggers only on time intervals (minimum 1 second). For real event conditions: use DML triggers (for DML events) or poll with an `EVENT` that runs every X seconds and checks whether the event occurred.
- **Chained/dependency jobs** → no native chains; create several `EVENTS` and coordinate them via a control table holding the last-run status to decide when to run the next step.
- Aurora MySQL has no native `JOB CLASS`/`WINDOW` resource-prioritization concepts.
