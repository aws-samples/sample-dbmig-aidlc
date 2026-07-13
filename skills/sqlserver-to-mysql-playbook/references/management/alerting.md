# Alerting features

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.management.alerting.html

**Conversion category:** Manual (One star feature compatibility)
**SCT automation:** N/A

## SQL Server

SQL Server Agent generates alerts. When running, it monitors Windows application log messages, performance counters, and WMI objects. When a new error event is detected, the agent checks MSDB for configured alerts and runs the specified action.

Alert categories:
* **SQL Server events** — by error number, severity level, database filter, and event text.
* **SQL Server performance conditions** — Object (counter category), Counter, Instance, and "Alert if counter / Value" (threshold + predicate: *falls below*, *becomes equal to*, *rises above*).
* **WMI events** — require the WMI namespace and a WQL query.

Alerts can be assigned to operators with schedule limitations and multiple response types: run an Agent job, send email/net send/pager notification. SQL Server Agent is pre-configured with several high-severity alerts (recommended to enable). Configure via SSMS or system stored procedures.

Example — alert for all severity-20 errors:

```sql
EXEC msdb.dbo.sp_add_alert
    @name = N'Severity 20 Error Alert',
    @severity = 20,
    @notification_message = N'A severity 20 Error has occurred. Initiating emergency procedure',
    @job_name = N'Error 20 emergency response';
```

## MySQL

Aurora MySQL doesn't support direct configuration of engine alerts. Use the **event notifications** infrastructure to collect history logs or receive near real-time notifications.

Amazon RDS uses **Amazon SNS** to provide event notifications (email, text, or HTTP endpoints for automation). Events are grouped into categories — you subscribe to categories, not individual events. You can subscribe for DB instances, DB clusters, snapshots, cluster snapshots, security groups, and parameter groups.

Note: For Aurora, some events occur at the cluster (not instance) level — you won't receive those if you subscribe to a DB instance. You can disable notifications without deleting a subscription (`Enabled = No` in the console, or via CLI/API). Subscriptions are identified by the SNS topic ARN.

Example walkthrough (create an event notification subscription):
1. Sign in to AWS, choose **RDS**.
2. Choose **Events** in the left nav.
3. Choose **Event subscriptions** → **Create event subscription**.
4. Enter the subscription **Name** and select a **Target** of ARN or Email (for email, enter **Topic** name and recipients).
5. Select the event source, choose event categories to monitor, and choose **Create**.
6. On the RDS dashboard, choose **Recent events**.

## Conversion notes
- AWS service replacement: SQL Server Agent alerts → **Amazon RDS event notifications via Amazon SNS**.
- You can only subscribe to event *categories*, not individual events as in SQL Server.
- Performance-threshold and WMI alerts have no direct equivalent; combine RDS event notifications with **Amazon CloudWatch** alarms for metric-based alerting.
- Typical pattern: create multiple subscriptions (e.g., one for logging events, one for critical production events).
