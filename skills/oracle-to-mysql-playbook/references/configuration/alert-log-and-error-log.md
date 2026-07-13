# Oracle Alert Log and MySQL Error Log

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.configuration.logs.html

**Conversion category:** N/A (feature compatibility: one star)
**SCT automation:** N/A

**Key difference:** Use Event Notification Subscriptions with Amazon SNS in place of Oracle's file-based alert log.

## Oracle

The primary Oracle error log is the **alert log**, containing verbose informational messages and errors, each timestamped. Filename format: `alert<sid>.log`.

Common events logged:

- Database startup or shutdown
- Redo log switches
- Errors and warnings beginning with `ORA-` followed by an Oracle error number
- Network and connection issues
- Links to detailed trace files for specific events

Location — inside the Automatic Diagnostics Repository (ADR):

```
$ADR_BASE/diag/rdbms/{DB-name}/{SID}/trace
```

Other server components (listener, ASM) maintain their own log files.

## MySQL

MySQL logs informational and error messages throughout the database/session lifecycle. In Aurora these are accessible via the Amazon RDS console.

Example Oracle vs MySQL error code mapping:

```
ORA-00001: unique constraint (string.string) violated.
→ Error 1062 (23000): Duplicate entry 'value' for key 'column'.
```

MySQL log types:

| Log type | Information written |
|---|---|
| Error log | Problems starting, running, or stopping `mysqld` |
| General query log | Client connections and statements received |
| Binary log | Statements that change data (also used for replication) |
| Relay log | Data changes received from a replication master |
| Slow query log | Queries exceeding `long_query_time` seconds |
| DDL log (metadata log) | Metadata operations performed by DDL statements |

**Access the Aurora MySQL error log:** RDS console → **Databases** → select instance → **Logs & events** → select the log for the relevant time window.

### Error log configuration parameters (Aurora DB Parameter Group)

| Parameter | Description |
|---|---|
| `log_error` | File name/path for the error log. Modifiable via Aurora DB Parameter Group. |
| `log_error_verbosity` | Message levels logged (error, warning, note). Modifiable via Aurora DB Parameter Group. |
| `USE SLOW LOG` (slow query threshold, ms) | Minimum execution time above which statements are logged. Modifiable via Aurora DB Parameter Group. |

> Note: modification of certain parameters such as `log_error` is turned off for Aurora MySQL instances.

## Conversion notes

- No direct equivalent to a single file-based `alert<sid>.log`; logs are split by type (error, general query, binary, relay, slow query, DDL) and surfaced through the RDS console.
- For proactive alerting, replace alert-log scanning with **Event Notification Subscriptions** wired to **Amazon SNS**.
- `ORA-` numeric error codes do not map 1:1 to MySQL error numbers; build an explicit code-mapping table for application error handling (e.g. `ORA-00001` → MySQL `1062`).
- In Aurora, log file paths/locations are managed; tune behavior through the DB parameter group rather than OS-level files. `log_error` itself is locked on Aurora.
