# Date and time functions for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.datetime.html

**Conversion category:** Assisted (Three star feature compatibility)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Verified the boundary-vs-complete-unit difference between SQL Server DATEDIFF and TIMESTAMPDIFF (wrong results otherwise), boundary-correct formulas, reversed DATEDIFF argument order, EOMONTH/DATEFROMPARTS/ISDATE/weekday mappings (verified), time zones.

## SQL Server

Date and time functions are scalar functions operating on temporal/numeric input. System date/time values derive from the server OS.

Most commonly used functions:

| Function | Purpose | Example | Result |
|---|---|---|---|
| `GETDATE`, `GETUTCDATE` | Current local or UTC date and time | `SELECT GETDATE()` | 2018-04-05 15:53:01.380 |
| `DATEPART`, `DAY`, `MONTH`, `YEAR` | Integer of specified date part | `SELECT MONTH(GETDATE()), YEAR(GETDATE())` | 4, 2018 |
| `DATEDIFF` | Integer count of date-part boundaries crossed between two dates | `SELECT DATEDIFF(DAY, GETDATE(), EOMONTH(GETDATE()))` | 25 |
| `DATEADD` | Datetime offset by interval on a date part | `SELECT DATEADD(DAY, 25, GETDATE())` | 2018-04-30 15:55:52.147 |
| `CAST`, `CONVERT` | Convert datetime to/from strings and other formats | `SELECT CAST(GETDATE() AS DATE)` / `SELECT CONVERT(VARCHAR(20), GETDATE(), 112)` | 2018-04-05 / 20180405 |

## MySQL

Aurora MySQL provides a richer set of scalar date/time functions than SQL Server. Some functions (e.g. `DATEDIFF`) look similar but behave significantly differently — take care.

| Function | Purpose | Example | Result |
|---|---|---|---|
| `NOW`, `LOCALTIME`, `CURRENT_TIMESTAMP`, `SYSDATE` | Current local date/time | `SELECT NOW()` | 2018-04-06 18:57:54 |
| `UTC_TIMESTAMP` | Current UTC date/time | `SELECT UTC_TIMESTAMP()` | 2018-04-07 04:57:54 |
| `SECOND`, `MINUTE`, `HOUR`, `DAY`, `WEEK`, `MONTH`, `YEAR` | Integer date part | `SELECT MONTH(NOW()), YEAR(NOW())` | 4, 2018 |
| `DATEDIFF` | Difference **in days only** between two dates | `SELECT DATEDIFF(NOW(),'2018-05-01')` | -25 |
| `TIMESTAMPDIFF` | Difference in a specified date part between two dates | `SELECT TIMESTAMPDIFF(DAY, NOW(),'2018-05-01')` | 24 |
| `DATE_ADD`, `DATE_SUB` | Datetime offset by interval | `SELECT DATE_ADD(NOW(),INTERVAL 1 DAY);` | 2018-04-07 19:35:32 |
| `CAST`, `CONVERT` | Convert datetime to/from strings | `SELECT CAST(GETDATE() AS DATE)` / `SELECT CONVERT(VARCHAR(20), GETDATE(), 112)` | 2018-04-05 / 20180405 |

`SYSDATE` returns the time at which it runs; `NOW` returns a constant time fixed at statement start. `SET TIMESTAMP` does not affect `SYSDATE`.

## Conversion notes

- Time zone handling and locale differ between the engines — review carefully (see Data Types).
- `DATEDIFF` semantics differ: Aurora MySQL `DATEDIFF(a, b)` computes **days only** and as `a − b` (reversed argument order versus SQL Server `DATEDIFF(day, start, end)`).
- **`TIMESTAMPDIFF` is not a drop-in for SQL Server `DATEDIFF`** (verified on 3.13 and 8.4.8): SQL Server counts **boundaries crossed**, MySQL counts **complete units**. `'2023-12-31'` → `'2024-01-01'`: SQL Server `DATEDIFF(year)` = 1, `TIMESTAMPDIFF(YEAR)` = 0; `'2024-01-31'` → `'2024-02-29'`: month 1 vs 0; `23:00` → `01:00` next day: day 1 vs 0. Boundary-correct conversions:
  - `DATEDIFF(day, s, e)` → `DATEDIFF(e, s)` (date parts only, verified = 1 for the example)
  - `DATEDIFF(month, s, e)` → `(YEAR(e) - YEAR(s)) * 12 + MONTH(e) - MONTH(s)`
  - `DATEDIFF(year, s, e)` → `YEAR(e) - YEAR(s)`
  - `DATEDIFF(hour, s, e)` → `TIMESTAMPDIFF(HOUR, DATE_FORMAT(s, '%Y-%m-%d %H:00:00'), DATE_FORMAT(e, '%Y-%m-%d %H:00:00'))`
  Use `TIMESTAMPDIFF` only where the source logic really wants elapsed complete units.
- `EOMONTH(d)` → `LAST_DAY(d)`; `DATEFROMPARTS(y, m, d)` → `MAKEDATE(y, 1) + INTERVAL m-1 MONTH + INTERVAL d-1 DAY` or `STR_TO_DATE(CONCAT_WS('-', y, m, d), '%Y-%m-%d')`; `ISDATE(s)` → `STR_TO_DATE(s, fmt) IS NOT NULL` (invalid dates return NULL, verified).
- `DATEPART(weekday, d)` depends on `DATEFIRST` (default 7 = Sunday first → Sunday = 1); MySQL `DAYOFWEEK(d)` has Sunday = 1 (matches the default), `WEEKDAY(d)` has Monday = 0 (verified). Code that changed `DATEFIRST` needs explicit arithmetic.
- `SYSDATETIMEOFFSET()`/`AT TIME ZONE` → `CONVERT_TZ(…, 'UTC', 'Europe/Paris')` (named zones are pre-loaded on Aurora); the server runs in UTC.
- `GETDATE()` inside a long procedure: MySQL `NOW()` is fixed per **statement** (not per batch); use `SYSDATE()` for wall-clock time.
- `DATEADD` → `DATE_ADD`/`DATE_SUB`/`TIMESTAMPADD`; argument order and syntax differ and require a rewrite (uses `INTERVAL n UNIT`).
- `CAST`/`CONVERT` in Aurora MySQL are **not** used for style conversion; use `DATE_FORMAT` / `TIME_FORMAT`.
- `DATEPART` → `EXTRACT` (e.g. `EXTRACT(YEAR FROM NOW())`) or individual part functions.

| SQL Server function | Aurora MySQL function | Comments |
|---|---|---|
| `GETDATE`, `CURRENT_TIMESTAMP` | `NOW`, `LOCALTIME`, `CURRENT_TIMESTAMP`, `SYSDATE` | `CURRENT_TIMESTAMP` is ANSI standard and compatible; `SYSDATE` differs from `NOW` |
| `GETUTCDATE` | `UTC_TIMESTAMP` | |
| `DAY`, `MONTH`, `YEAR` | `DAY`, `MONTH`, `YEAR` | Compatible syntax |
| `DATEPART` | `EXTRACT` or individual part functions (`MICROSECOND`…`YEAR`, `DAYNAME`, `DAYOFWEEK`, `QUARTER`, etc.) | `EXTRACT` is generic `DATEPART` |
| `DATEDIFF` | `TIMESTAMPDIFF` | Aurora `DATEDIFF` is days-only |
| `DATEADD` | `DATE_ADD`, `DATE_SUB`, `TIMESTAMPADD` | Different argument order/syntax |
| `CAST`, `CONVERT` | `DATE_FORMAT`, `TIME_FORMAT` | Aurora `CAST`/`CONVERT` not for style conversion |
