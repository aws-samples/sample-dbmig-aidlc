# Oracle Alert Log and MySQL Error Log

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.configuration.logs.html

**Conversion category:** N/A (feature compatibility: one star)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Replaced the nonexistent USE SLOW LOG parameter, verified log_error path and verbosity on both versions, CloudWatch export, error-code mapping table.

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
| `slow_query_log`, `long_query_time` (seconds, default 10) | Slow-query logging and its threshold. Modifiable via the DB parameter group. (The original listed a nonexistent `USE SLOW LOG` parameter.) |

> Note: modification of certain parameters such as `log_error` is turned off for Aurora MySQL instances.

## Conversion notes

- No direct equivalent to a single file-based `alert<sid>.log`; logs are split by type (error, general query, binary, relay, slow query, DDL) and surfaced through the RDS console.
- For proactive alerting, replace alert-log scanning with **Event Notification Subscriptions** wired to **Amazon SNS**.
- `ORA-` numeric error codes do not map 1:1 to MySQL error numbers; build an explicit code-mapping table for application error handling (e.g. `ORA-00001` → MySQL `1062`).
- In Aurora, log file paths/locations are managed; tune behavior through the DB parameter group rather than OS-level files. `log_error` itself is locked on Aurora (`/rdsdbdata/log/error/mysql-error.log`, verified); `log_error_verbosity` is 3 (errors, warnings, notes) by default on 3.13 and 8.4.
- **Export the error log to CloudWatch Logs** (`--cloudwatch-logs-export-configuration EnableLogTypes=error,slowquery,audit`) and alarm on metric filters; this is the closest equivalent to monitoring `alert.log`. Instance-level events (failover, reboot, storage) come through RDS event subscriptions → SNS / EventBridge.
- Common error-code mappings for application handlers: `ORA-00001` → 1062 (23000); `ORA-01400` (NULL into NOT NULL) → 1048; `ORA-02291`/`ORA-02292` (FK) → 1452 / 1451; `ORA-00060` (deadlock) → 1213 (40001); `ORA-01403` (no data) → 1329 / SQLSTATE 02000 inside routines; `ORA-30006` / lock wait → 1205; `ORA-01722` (invalid number) → 1366/1292 only in strict mode, otherwise a warning; `ORA-20000..20999` (`RAISE_APPLICATION_ERROR`) → `SIGNAL SQLSTATE '45000'` with a chosen `MYSQL_ERRNO`.
