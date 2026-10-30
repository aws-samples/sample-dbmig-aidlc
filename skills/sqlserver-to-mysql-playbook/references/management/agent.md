# SQL Server Agent and MySQL Agent

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.management.agent.html

**Conversion category:** Manual (No feature compatibility)
**SCT automation:** No automation

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): event_scheduler is ON by default (verified), Lambda timeout is 15 min, EventBridge Scheduler/Step Functions, DISABLE ON SLAVE works on both, DISABLE ON REPLICA only on 8.4 (verified), fixed the WHERE/GROUP BY example, job-history and overlap guidance.

## SQL Server

SQL Server Agent provides two main functions: scheduling automated maintenance and backup jobs, and alerting. Other SQL built-in frameworks such as replication also use SQL Server Agent jobs under the covers. Maintenance plans, backups, and alerting are covered in separate sections.

## MySQL

Aurora MySQL provides a native, in-database scheduler limited to the cluster scope; it can't manage multiple clusters, and there are no native alerting capabilities similar to SQL Server Agent alerts.

Amazon RDS doesn't provide an external scheduling agent, but **Amazon EventBridge Scheduler** (successor of CloudWatch Events rules) can run **Lambda functions**, **Step Functions** workflows or **ECS tasks** on cron or rate schedules. *(corrected)* The Lambda timeout is **15 minutes** (not 5); use Step Functions or an ECS/Fargate task for longer jobs. Other options:
1. Run a SQL Server purely for its Agent.
2. Use a t2 instance or container to schedule code with Cron (a t2.nano is cheap and runs tasks indefinitely).

### Aurora MySQL Database Events

Aurora MySQL provides a native, in-database scheduling framework. Events run on a dedicated thread (visible in the process list). *(corrected)* The global `event_scheduler` is **ON by default** on Aurora MySQL 3 and 8.4 (verified on 3.13 and 8.4.8). Event errors are written to the error log. Event metadata is viewable via `INFORMATION_SCHEMA.EVENTS`.

Syntax:

```sql
CREATE EVENT <Event Name>
    ON SCHEDULE <Schedule>
    [ON COMPLETION [NOT] PRESERVE][ENABLE | DISABLE | DISABLE ON SLAVE]   -- 8.4 also accepts DISABLE ON REPLICA; 3.13 does not (verified)
    [COMMENT 'string']
    DO <Event Body>;

<Schedule>:
    AT <Time Stamp> [+ INTERVAL <Interval>] ...
    | EVERY <Interval>
    [STARTS <Time Stamp> [+ INTERVAL <Interval>] ...]
    [ENDS <Time Stamp> [+ INTERVAL <Interval>] ...]

<Interval>:
    quantity {YEAR | QUARTER | MONTH | DAY | HOUR | MINUTE |
        WEEK | SECOND | YEAR_MONTH | DAY_HOUR | DAY_MINUTE |
        DAY_SECOND | HOUR_MINUTE | HOUR_SECOND | MINUTE_SECOND}
```

Examples:

```sql
-- Run once, five hours after creation
CREATE EVENT Update_T1_In_5_Hours
    ON SCHEDULE AT CURRENT_TIMESTAMP + INTERVAL 5 HOUR
    DO
        INSERT INTO LoginStatistics
        SELECT UserID, COUNT(*) AS LoginAttempts
        FROM Logins AS L
        WHERE LoginData = '20180502'     -- the original put WHERE after GROUP BY (syntax error)
        GROUP BY UserID;

-- Run every 4 hours, delete old sessions
CREATE EVENT Clear_Old_Sessions
    ON SCHEDULE EVERY 4 HOUR
    DO
        DELETE FROM Sessions
        WHERE LastCommandTime < CURRENT_TIMESTAMP - INTERVAL 4 HOUR;

-- Weekly index rebuild calling a procedure with parameters
CREATE EVENT Rebuild_Indexes
    ON SCHEDULE EVERY 1 WEEK
    DO
        CALL IndexRebuildProcedure(1, 80);
```

## Conversion notes
- No direct equivalent — SQL Server Agent is not compatible and has no SCT automation.
- For in-cluster scheduling, use Aurora MySQL Database Events (`CREATE EVENT`); `event_scheduler` is already ON on Aurora.
- Agent job steps → one event per job calling a procedure; multi-step jobs with success/failure branching → a procedure with handlers, or Step Functions for cross-system steps. Job history (`msdb.dbo.sysjobhistory`) → write start/end/error rows to a job-log table in the procedure (event failures only reach the error log).
- Events run only on the writer and keep running after failover on the new writer; schedules use the event's time zone (UTC on Aurora by default).
- Guard against overlapping runs with `GET_LOCK('job_x', 0)` at the start of the procedure.
- For cross-cluster scheduling/orchestration, use **CloudWatch Events + AWS Lambda**, a dedicated scheduling EC2 instance/container with Cron, or a standalone SQL Server kept only for its Agent.
- Watch the Lambda 15-minute timeout for long maintenance operations.
- Alerting and maintenance-plan functionality of the Agent map to separate features — see Alerting and Maintenance plans references.
