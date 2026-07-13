# Configuring Session Options

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.configuration.sessionoptions.html

**Conversion category:** Assisted (two-star feature compatibility)
**SCT automation:** N/A
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

Aurora MySQL 5.7 adds variables not present in standalone MySQL 5.7, prefixed with `Aurora` or `AWS`. Unlike standalone MySQL, Aurora does **not** expose the configuration file: cluster-level parameters live in DB cluster parameter groups; instance-level parameters in DB parameter groups. Some parameters can't be modified or were removed.

View sessions:

```sql
SELECT * FROM information_schema.PROCESSLIST;
SHOW PROCESSLIST;
```

Change session isolation level and SQL mode:

```sql
SET sql_mode = 'ANSI_QUOTES';
SET SESSION TRANSACTION ISOLATION LEVEL 'READ-COMMITTED';
SET SESSION tx_isolation = 'READ-COMMITTED';
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
- `DATEFORMAT` → `date_format` (deprecated; no alternative).
- `LOCK_TIMEOUT` → `lock_wait_timeout` (set in DB parameter groups).
- `ANSI_NULLS` → N/A (set via `sql_mode` system variable).
- `ANSI_PADDING` → `PAD_CHAR_TO_FULL_LENGTH`.
- `IMPLICIT_TRANSACTIONS` → `autocommit` (default commits automatically in both; syntax compatible aside from the `SESSION` keyword).
- `TRANSACTION ISOLATION LEVEL` → `SET SESSION TRANSACTION ISOLATION LEVEL`.
- `IDENTITY_INSERT` → see Identity and Sequences.
- `LANGUAGE` → `lc_time_names` (set in a DB parameter group; `lc_messages` not supported in Aurora MySQL).
- `QUOTED_IDENTIFIER` → `ANSI_QUOTES` (a value for `sql_mode`).
- `NOCOUNT` → N/A and not needed.
- `SHOWPLAN_ALL`/`TEXT`/`XML`, `STATISTICS IO`/`XML`/`PROFILE`/`TIME` → see Run Plans.
- `CONCAT_NULL_YIELDS_NULL` → N/A (Aurora MySQL always returns NULL for NULL concatenation).
- `ROWCOUNT` → `sql_select_limit` (only affects `SELECT`, unlike `ROWCOUNT` which also affects all DML).
- Aurora MySQL has far more configurable parameters than SQL Server; many are managed through parameter groups rather than per-session `SET`.
