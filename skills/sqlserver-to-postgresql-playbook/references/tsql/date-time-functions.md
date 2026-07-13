# Date and Time Functions

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.datetime.html

**Conversion category:** Automatic (four-star feature compatibility, four-star automation)
**SCT automation:** Four-star automation level; SCT action code index: Data Types

## SQL Server

Date/time functions are scalar functions operating on temporal/numeric input. System date/time values derive from the server OS.

Common functions:

| Function | Purpose | Example | Result |
|---|---|---|---|
| `GETDATE`, `GETUTCDATE` | current local/UTC date and time | `SELECT GETDATE()` | `2018-04-05 15:53:01.380` |
| `DATEPART`, `DAY`, `MONTH`, `YEAR` | integer of a DATEPART | `SELECT MONTH(GETDATE()), YEAR(GETDATE())` | `4, 2018` |
| `DATEDIFF` | DATEPART boundaries crossed between two dates | `SELECT DATEDIFF(DAY, GETDATE(), EOMONTH(GETDATE()))` | `25` |
| `DATEADD` | datetime offset by interval | `SELECT DATEADD(DAY, 25, GETDATE())` | `2018-04-30 15:55:52.147` |
| `CAST`, `CONVERT` | convert datetime to/from strings/formats | `SELECT CAST (GETDATE() AS DATE)` / `SELECT CONVERT (VARCHAR(20), GETDATE(), 112)` | `2018-04-05` / `20180405` |

## PostgreSQL

Aurora PostgreSQL provides a richer set of date/time functions than SQL Server. Some look similar but behave significantly differently — take care migrating temporal logic.

Key functions:

| PostgreSQL function | Definition |
|---|---|
| `AGE` | Subtract from `current_date` |
| `CLOCK_TIMESTAMP` | Current date and time |
| `CURRENT_DATE` | Current date |
| `CURRENT_TIME` | Current time of day |
| `CURRENT_TIMESTAMP` | Current date/time (start of current transaction) |
| `DATE_PART` | Get subfield (equivalent to extract) |
| `DATE_TRUNC` | Truncate to specified precision |
| `EXTRACT` | Get subfield |
| `ISFINITE` | Test for finite interval |
| `JUSTIFY_DAYS` | Represent 30-day periods as months |
| `JUSTIFY_HOURS` | Represent 24-hour periods as days |
| `JUSTIFY_INTERVAL` | Adjust interval using justify_days + justify_hours |
| `LOCALTIME` | Current time of day |
| `MAKE_DATE` | Create date from year/month/day |
| `MAKE_INTERVAL` | Create interval from y/m/w/d/h/m/s |
| `MAKE_TIME` | Create time from hour/minute/sec |
| `MAKE_TIMESTAMP` | Create timestamp from fields |
| `MAKE_TIMESTAMPTZ` | Create timestamptz (current tz if unspecified) |
| `NOW` | Current date and time |
| `STATEMENT_TIMESTAMP` | Current date and time |
| `TIMEOFDAY` | Current date/time as text string |
| `TRANSACTION_TIMESTAMP` | Current date and time |
| `TO_TIMESTAMP` | Convert Unix epoch to timestamp |

## Summary

| SQL Server function | Aurora PostgreSQL function |
|---|---|
| `GETDATE`, `CURRENT_TIMESTAMP` | `NOW`, `CURRENT_DATE`, `CURRENT_TIME`, `CURRENT_TIMESTAMP` |
| `GETUTCDATE` | `current_timestamp at time zone 'utc'` |
| `DAY`, `MONTH`, `YEAR` | `EXTRACT(DAY/MONTH/YEAR FROM TIMESTAMP timestamp_value)` |
| `DATEPART` | `EXTRACT`, `DATE_PART` |
| `DATEDIFF` | `DATE_PART` |
| `DATEADD` | `+ INTERVAL 'X days/months/years'` |
| `CAST` and `CONVERT` | `CAST` |

## Conversion notes
- Function names differ; behavior is largely equivalent for common cases and well-automated by SCT.
- `DATEDIFF` has no direct equivalent — compute with `DATE_PART` on the difference, or subtract and extract.
- `DATEADD` becomes arithmetic with `INTERVAL` literals.
- `GETUTCDATE` → `current_timestamp at time zone 'utc'`.
- `CONVERT(..., style)` date formatting → use `TO_CHAR` with a format mask (see CAST/CONVERT reference).
- PostgreSQL distinguishes `clock_timestamp()` (real-time) vs `now()`/`transaction_timestamp()` (transaction start) vs `statement_timestamp()` — verify which semantics the original code expects.
