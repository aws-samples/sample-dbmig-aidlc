# Oracle Alert Log and PostgreSQL Error Log

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.configuration.errorlog.html

**Conversion category:** N/A (config/operations topic) — feature compatibility: one star
**SCT automation:** N/A. Key difference: use [Event Notifications Subscription] with Amazon SNS.

## Oracle

The primary Oracle error log is the **Alert Log**, containing verbose database activity (informational messages and errors), each event timestamped. Filename format: `alert<sid>.log`.

It is the first place to look when troubleshooting. Common logged events:
* Database startup or shutdown
* Database redo log switch
* Database errors and warnings — begin with `ORA-` followed by an Oracle error number
* Network and connection issues
* Links to detailed trace files for specific events

Location — inside the Automatic Diagnostics Repository (ADR), a hierarchical file-based repository:

```
$ADR_BASE/diag/rdbms/{DB-name}/{SID}/trace
```

Other Oracle server components (database listener, Automatic Storage Manager / ASM) have their own unique log files.

## PostgreSQL

PostgreSQL provides detailed logging/reporting of errors over the database and session lifecycle. In Amazon Aurora, these messages are accessible through the **Amazon RDS console**.

**Oracle vs PostgreSQL error codes** (example):

| Oracle | PostgreSQL |
|---|---|
| `ORA-00001: unique constraint (string.string) violated` | `SQLSTATE[23505]: Unique violation: 7 ERROR: duplicate key value violates unique constraint "constraint_name"` |

**PostgreSQL error log severity types:**

| Log type | Information written to log |
|---|---|
| `DEBUG1`…`DEBUG5` | Successively more-detailed information for developers |
| `INFO` | Information implicitly requested by the user |
| `NOTICE` | Information that might be helpful to users |
| `WARNING` | Warnings of likely problems |
| `ERROR` | Reports an error that caused the current command to abort |
| `LOG` | Information of interest to administrators |
| `FATAL` | Error that caused the current session to abort |
| `PANIC` | Error that caused all database sessions to abort |

**Accessing the error log (Aurora/RDS console):** Sign in → RDS → **Databases** → select your database → **Logs & events** → scroll to **Logs** → select a log (e.g., for the hour data had problems) → choose the log to view.

**PostgreSQL error log configuration parameters** (all modifiable via an Aurora Database Parameter Group):

| Parameter | Description |
|---|---|
| `log_filename` | Sets the file name pattern for log files |
| `log_rotation_age` | (min) Automatic log file rotation after N minutes |
| `log_rotation_size` | (kB) Automatic log file rotation after N kilobytes |
| `log_min_messages` | Sets the message levels that are logged (`DEBUG`, `ERROR`, `INFO`, etc.) |
| `log_min_error_statement` | Logs all statements generating an error at or above this level (`DEBUG`, `ERROR`, `INFO`, etc.) |
| `log_min_duration_statement` | Minimum run time (ms) above which statements are logged |

## Conversion notes

- No single file equivalent to Oracle's Alert Log; Aurora exposes logs through the RDS console rather than the OS filesystem.
- For event-driven alerting (analogous to monitoring the Alert Log), use **Event Notifications Subscription** with **Amazon SNS**.
- Aurora **disables** modification of certain parameters: `log_directory` (destination directory for log files) and `logging_collector` (subprocess that captures stderr/csvlogs into files) — because Aurora restricts OS access.
- Map `ORA-` error numbers to PostgreSQL `SQLSTATE` codes when porting error-handling logic.
