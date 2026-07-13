# Alerting features

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.alerting.html

**Conversion category:** N/A (one-star feature compatibility)
**SCT automation:** N/A

Key difference: Use Amazon RDS event notification with Amazon Simple Notification Service (Amazon SNS).

## SQL Server

SQL Server Agent generates alerts. While running, it monitors Windows application log messages, performance counters, and WMI objects. On a new error event, it checks `msdb` for configured alerts and runs the specified action.

Alert categories:
- SQL Server events (Error Number, Severity Level, Database, Event Text filters).
- SQL Server performance conditions (Object, Counter, Instance, "Alert if counter" value/predicate — falls below / becomes equal to / rises above).
- WMI events (require WMI namespace + WQL query).

Alerts can be assigned to operators with schedule limits and multiple responses: run an Agent job, send Email, Net Send, or pager notification. Configured via SSMS or system stored procedures. Agent ships with several pre-configured high-severity alerts (recommended to enable).

Example — configure an alert for all errors with severity 20:

```sql
EXEC msdb.dbo.sp_add_alert
  @name = N'Severity 20 Error Alert',
  @severity = 20,
  @notification_message = N'A severity 20 Error has occurred. Initiating emergency procedure',
  @job_name = N'Error 20 emergency response';
```

## PostgreSQL

Aurora PostgreSQL doesn't support direct configuration of engine alerts. Use the Event Notifications infrastructure: Amazon RDS uses Amazon SNS to deliver event notifications (email, SMS, or HTTP endpoints for automation).

- Events are grouped into categories; you subscribe to categories, not individual events.
- Subscribe for DB instances, DB clusters, snapshots, security groups, and parameter groups (e.g., subscribe to Backup category for one instance).
- For Aurora, some events occur at the cluster (not instance) level — you won't receive those if subscribed only to a DB instance.
- Notifications can be disabled without deleting a subscription (Enabled = No in the console, CLI, or API).
- Subscriptions are identified by an SNS topic ARN. The RDS console creates ARNs automatically; with CLI/API you create the ARN via the SNS console/API.

Example — create an event notification subscription (console):
1. Sign in, choose **RDS**.
2. Choose **Events** in the left nav.
3. Choose **Event subscriptions** → **Create event subscription**.
4. Enter the subscription **Name**, choose a **Target** (ARN or Email); for email enter **Topic** name and recipients.
5. Select the event source, choose event categories, choose **Create**.
6. View results under **Recent events** on the RDS dashboard.

### Raising errors from within the database — PostgreSQL log severity levels

| Log type | Information written to log |
|---|---|
| `DEBUG1`…`DEBUG5` | Successively more detailed information for developers. |
| `INFO` | Information implicitly requested by the user. |
| `NOTICE` | Information that might be helpful to users. |
| `WARNING` | Warnings of likely problems. |
| `ERROR` | Reports the error that caused the current command to abort. |
| `LOG` | Information of interest to administrators. |
| `FATAL` | Error that caused the current session to abort. |
| `PANIC` | Error that caused all database sessions to abort. |

Parameters controlling log/error file placement (modify via an Aurora DB Parameter Group):

| Parameter | Description |
|---|---|
| `log_filename` | File name pattern for log files. |
| `log_rotation_age` | (min) Rotate log file after N minutes. |
| `log_rotation_size` | (kB) Rotate log file after N kilobytes. |
| `log_min_messages` | Message levels that are logged (`DEBUG`, `ERROR`, `INFO`, …). |
| `log_min_error_statement` | Log all statements generating errors at or above this level. |
| `log_min_duration_statement` | Minimum run time (ms) above which statements are logged. |

Note: `log_directory` and `logging_collector` modifications are disabled for an Aurora PostgreSQL instance.

## Conversion notes

- No direct engine-alert equivalent — replace Agent alerts with Amazon RDS event notifications + Amazon SNS.
- AWS service replacement: Amazon SNS for notification delivery (email/SMS/HTTP).
- Aurora cluster-level events require subscribing at the cluster level, not just the instance.
- Application-level error raising maps to PostgreSQL log severity levels controlled through DB parameter groups.
