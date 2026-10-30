# Configuring Session Options

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.configuration.sessionoptions.html

**Conversion category:** Assisted (two-star feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Fixed invalid examples (quoted isolation level, removed tx_isolation, sql_mode overwrite); date_format removed; LOCK_TIMEOUT units; string + is numeric addition (verified); SET GLOBAL denied; connection-init guidance.
**Key difference:** SET options are significantly different, except for transaction isolation control.

## SQL Server

Session options are run-time settings controlling how the server handles data per session (a session = login → disconnect / `exec sp_reset_connection`). Set global session options with the `SET` T-SQL command. Code modules (stored procedures, functions) store their own run-context settings with the code.

View current sessions via `sp_who_system` and the `sysprocesses` system table.

`SET` command categories and settings:

```
SET
Date and time:    DATEFIRST | DATEFORMAT
Locking:          DEADLOCK_PRIORITY | SET LOCK_TIMEOUT
Miscellaneous:    CONCAT_NULL_YIELDS_NULL | CURSOR_CLOSE_ON_COMMIT | FIPS_FLAGGER |
                  SET IDENTITY_INSERT | LANGUAGE | OFFSETS | QUOTED_IDENTIFIER
Query Execution:  ARITHABORT | ARITHIGNORE | FMTONLY | NOCOUNT | NOEXEC |
                  NUMERIC_ROUNDABORT | PARSEONLY | QUERY_GOVERNOR_COST_LIMIT |
                  ROWCOUNT | TEXTSIZE | ANSI_DEFAULTS | ANSI_NULL_DFLT_OFF |
                  ANSI_NULL_DFLT_ON | ANSI_NULLS | ANSI_PADDING | ANSI_WARNINGS
Execution Stats:  FORCEPLAN | SHOWPLAN_ALL | SHOWPLAN_TEXT | SHOWPLAN_XML |
                  STATISTICS IO | STATISTICS XML | STATISTICS PROFILE | STATISTICS TIME
Transactions:     IMPLICIT_TRANSACTIONS | REMOTE_PROC_TRANSACTIONS |
                  TRANSACTION ISOLATION LEVEL | XACT_ABORT
```

**SET ROWCOUNT for DML (deprecated):** Up to SQL Server 2008 R2, `SET ROWCOUNT` limited rows affected by `INSERT`/`UPDATE`/`DELETE`. From SQL Server 2012 it is ignored for DML. Use `TOP` instead (converts to `LIMIT` in Aurora MySQL):

```sql
WHILE @@ROWCOUNT > 0
BEGIN
    DELETE TOP (5000)
    FROM MyTable
    WHERE ForDelete = 1;
END
```

Example — `SET` within a stored procedure (settings affect the run scope and sub-scopes; the calling scope resumes its original settings on exit):

```sql
CREATE PROCEDURE <ProcedureName>
AS
BEGIN
    <Some non critical transaction code>
    SET TRANSACTION_ISOLATION_LEVEL SERIALIZABLE;
    SET XACT_ABORT ON;
    <Some critical transaction code>
END
```

## MySQL

Aurora MySQL supports hundreds of Server System Variables at global and session levels.

```sql
SHOW SESSION VARIABLES;
-- 532 rows returned
```

Aurora MySQL 3 and 8.4 add variables not present in community MySQL, prefixed with `aurora_` or `aws_`. Unlike standalone MySQL, Aurora does **not** expose the configuration file: cluster-level parameters live in DB cluster parameter groups; instance-level parameters in DB parameter groups. Some parameters can't be modified or were removed.

View sessions:

```sql
SELECT * FROM information_schema.PROCESSLIST;
SHOW PROCESSLIST;
```

Change session isolation level and SQL mode:

```sql
SET sql_mode = CONCAT(@@sql_mode, ',ANSI_QUOTES');          -- append; a plain SET replaces STRICT_TRANS_TABLES
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;     -- no quotes (the quoted form is a syntax error, verified)
SET SESSION transaction_isolation = 'READ-COMMITTED';       -- tx_isolation was removed in 8.0 (error 1193, verified)
```

`SET SESSION` is the equivalent of T-SQL `SET`.

**Converting SET ROWCOUNT for DML** — cannot be converted automatically; rewrite to `TOP` before running AWS SCT, or change manually. Aurora MySQL `LIMIT` equivalent:

```sql
WHILE row_count() > 0
DO
    DELETE
    FROM MyTable
    WHERE ForDelete = 1
    LIMIT 5000;
END WHILE;
```

## Conversion notes

Mapping of common SQL Server session options to Aurora MySQL system variables:

- `DATEFIRST` → `default_week_format` (behaves differently; only Sunday/Monday as start of week; also controls week-one definition and zero/one-based `WEEK` value).
- `DATEFORMAT` → no equivalent: the `date_format` variable was removed in MySQL 8.0 (error 1193, verified). MySQL always parses date literals as `YYYY-MM-DD`; convert other formats with `STR_TO_DATE`.
- `LOCK_TIMEOUT ms` → `SET SESSION innodb_lock_wait_timeout = seconds` for row locks (default 50 s, verified); `lock_wait_timeout` (default 1 year) is for metadata locks. Note the unit change from milliseconds to seconds.
- `ANSI_NULLS` → N/A (set via `sql_mode` system variable).
- `ANSI_PADDING` → `PAD_CHAR_TO_FULL_LENGTH` in `sql_mode` (still accepted, verified, but deprecated). Trailing-space behavior is mostly a collation matter in MySQL 8 (NO PAD `_0900_` collations), see `../tsql/collations.md`.
- `IMPLICIT_TRANSACTIONS ON` → `SET autocommit = 0`; `OFF` (the SQL Server default) → `autocommit = 1` (the MySQL default).
- `TRANSACTION ISOLATION LEVEL` → `SET SESSION TRANSACTION ISOLATION LEVEL`.
- `IDENTITY_INSERT` → see Identity and Sequences.
- `LANGUAGE` → `lc_time_names` (session `SET` or the cluster parameter group) and `lc_messages` (session `SET` only; it is not in the Aurora parameter groups). Both verified on 3.13 and 8.4 *(corrected: the playbook said `lc_messages` is not supported)*.
- `QUOTED_IDENTIFIER` → `ANSI_QUOTES` (a value for `sql_mode`).
- `NOCOUNT` → N/A and not needed.
- `SHOWPLAN_ALL`/`TEXT`/`XML`, `STATISTICS IO`/`XML`/`PROFILE`/`TIME` → see Run Plans.
- `CONCAT_NULL_YIELDS_NULL` → N/A (`CONCAT` returns NULL if any argument is NULL; `CONCAT_WS` skips NULLs).
- **String `+` concatenation does not exist:** `'a' + 'b'` is numeric addition and returns `0`, and `'abc' + 1` returns `1`, with only a warning (verified). Every T-SQL `+` on strings must become `CONCAT()`.
- `ROWCOUNT` → `sql_select_limit` (only affects `SELECT`, unlike `ROWCOUNT` which also affects all DML).
- `SET GLOBAL` is denied to the Aurora master user (error 1227, verified); instance-wide defaults go in parameter groups.
- Set session options the converted code relies on (`sql_mode`, `transaction_isolation`, `time_zone`, `group_concat_max_len`) in the connection initialization of the application, not in each procedure; each `SET` pins RDS Proxy connections.
- Aurora MySQL has far more configurable parameters than SQL Server; many are managed through parameter groups rather than per-session `SET`.
