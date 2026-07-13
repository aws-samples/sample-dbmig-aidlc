# SQL Server Agent and MySQL Agent

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.management.agent.html

**Conversion category:** Manual (No feature compatibility)
**SCT automation:** No automation

## SQL Server

SQL Server Agent provides two main functions: scheduling automated maintenance and backup jobs, and alerting. Other SQL built-in frameworks such as replication also use SQL Server Agent jobs under the covers. Maintenance plans, backups, and alerting are covered in separate sections.

## MySQL

Aurora MySQL provides a native, in-database scheduler limited to the cluster scope; it can't manage multiple clusters, and there are no native alerting capabilities similar to SQL Server Agent alerts.

Amazon RDS doesn't provide an external scheduling agent, but **CloudWatch Events** can specify a cron-like schedule to run **Lambda functions** (custom code in C#, NodeJS, Java, or Python). Note the AWS Lambda 5-minute timeout limit — long-running tasks like index rebuilds may not fit. Other options:
1. Run a SQL Server purely for its Agent.
2. Use a t2 instance or container to schedule code with Cron (a t2.nano is cheap and runs tasks indefinitely).

### Aurora MySQL Database Events

Aurora MySQL provides a native, in-database scheduling framework. Events run on a dedicated thread (visible in the process list). The global `event_scheduler` must be turned on explicitly (default `OFF`). Event errors are written to the error log. Event metadata is viewable via `INFORMATION_SCHEMA.EVENTS`.

Syntax:

```sql
CREATE EVENT <Event Name>
    ON SCHEDULE <Schedule>
    [ON COMPLETION [NOT] PRESERVE][ENABLE | DISABLE | DISABLE ON SLAVE]
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
        GROUP BY UserID
        WHERE LoginData = '20180502';

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
- For in-cluster scheduling, use Aurora MySQL Database Events (`CREATE EVENT`); enable `event_scheduler` first.
- For cross-cluster scheduling/orchestration, use **CloudWatch Events + AWS Lambda**, a dedicated scheduling EC2 instance/container with Cron, or a standalone SQL Server kept only for its Agent.
- Watch the Lambda 5-minute timeout for long maintenance operations.
- Alerting and maintenance-plan functionality of the Agent map to separate features — see Alerting and Maintenance plans references.
