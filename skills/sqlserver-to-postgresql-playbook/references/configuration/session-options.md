# Configuring Session Options

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.configuration.sessionoptions.html

**Conversion category:** N/A (Two-star feature compatibility)
**SCT automation:** N/A — `SET ROWCOUNT` for DML cannot be converted automatically; SCT can convert `SET ROWCOUNT`→`TOP` patterns automatically when already rewritten.

**Key difference:** `SET` options are significantly different, except for transaction isolation control.

## SQL Server

Session options are run-time settings controlling how the server handles data for individual sessions (a session = login to disconnect, or `exec sp_reset_connection` for connection pooling). Set global session options with the `SET` T-SQL command. Server code modules (stored procedures, functions) save their own run-context settings with the code to guarantee result validity. Explicit `SET` commands affect their run scope and sub-scopes; after a called scope exits, the calling scope resumes its original settings.

View current session metadata with `sp_who_system` and the `sysprocesses` system table.

### Syntax / categories

`SET` command categories and settings:
- **Date and time:** `DATEFIRST` | `DATEFORMAT`
- **Locking:** `DEADLOCK_PRIORITY` | `SET LOCK_TIMEOUT`
- **Miscellaneous:** `CONCAT_NULL_YIELDS_NULL` | `CURSOR_CLOSE_ON_COMMIT` | `FIPS_FLAGGER` | `SET IDENTITY_INSERT` | `LANGUAGE` | `OFFSETS` | `QUOTED_IDENTIFIER`
- **Query Execution:** `ARITHABORT` | `ARITHIGNORE` | `FMTONLY` | `NOCOUNT` | `NOEXEC` | `NUMERIC_ROUNDABORT` | `PARSEONLY` | `QUERY_GOVERNOR_COST_LIMIT` | `ROWCOUNT` | `TEXTSIZE`
- **ANSI:** `ANSI_DEFAULTS` | `ANSI_NULL_DFLT_OFF` | `ANSI_NULL_DFLT_ON` | `ANSI_NULLS` | `ANSI_PADDING` | `ANSI_WARNINGS`
- **Execution Stats:** `FORCEPLAN` | `SHOWPLAN_ALL` | `SHOWPLAN_TEXT` | `SHOWPLAN_XML` | `STATISTICS IO` | `STATISTICS XML` | `STATISTICS PROFILE` | `STATISTICS TIME`
- **Transactions:** `IMPLICIT_TRANSACTIONS` | `REMOTE_PROC_TRANSACTIONS` | `TRANSACTION ISOLATION LEVEL` | `XACT_ABORT`

Example — use `SET` within a stored procedure:

```sql
CREATE PROCEDURE <ProcedureName>
AS
BEGIN
  <Some non-critical transaction code>
  SET TRANSACTION_ISOLATION_LEVEL SERIALIZABLE;
  SET XACT_ABORT ON;
  <Some critical transaction code>
END
```

**`SET ROWCOUNT` for DML (deprecated as of SQL Server 2008 R2):** Previously used to limit rows affected by `INSERT`/`UPDATE`/`DELETE` (e.g. batching large deletes to avoid transaction-log issues):

```sql
SET ROWCOUNT 5000;
WHILE @@ROWCOUNT > 0
BEGIN
  DELETE FROM MyTable
  WHERE ForDelete = 1;
END
```

From SQL Server 2012, `SET ROWCOUNT` is ignored for `INSERT`/`UPDATE`/`DELETE`. Use `TOP` instead (SCT can convert `TOP`→`LIMIT`):

```sql
WHILE @@ROWCOUNT > 0
BEGIN
  DELETE TOP (5000)
  FROM MyTable
  WHERE ForDelete = 1;
END
```

## PostgreSQL

Aurora PostgreSQL supports hundreds of server system variables at global and session levels. Session-modifiable parameters are configured with `SET SESSION` (applies only to the current session). List settable parameters:

```sql
SELECT * FROM pg_settings where context = 'user';
```

Commonly used session parameters:
- `client_encoding` — connected client character set.
- `force_parallel_mode` — forces parallel query for the session.
- `lock_timeout` — max duration to wait for a database lock to release.
- `search_path` — schema search order for non-schema-qualified object names.
- `transaction_isolation` — current transaction isolation level for the session.

View variables via the psql command line, Aurora cluster/instance parameters, or system variable interfaces.

**Converting `SET ROWCOUNT` for DML:** Code using `SET ROWCOUNT` cannot be converted automatically. Rewrite to `TOP` before running SCT, or change manually afterward. The `TOP`-batched delete maps to a `LIMIT`-based loop:

```sql
WHILE row_count() > 0 LOOP
  DELETE FROM num_test
  WHERE ctid IN (
    SELECT ctid
    FROM num_test
    LIMIT 10)
END LOOP;
```

Example — change session date style:

```sql
SET SESSION DateStyle to POSTGRES, DMY;
SELECT NOW();
-- Sat 09 Sep 11:03:43.597202 2017 UTC

SET SESSION DateStyle to ISO, MDY;
SELECT NOW();
-- 2017-09-09 11:04:01.3859+00
```

## Conversion notes

Mapping of common SQL Server session options to Aurora PostgreSQL system variables:

| Category | SQL Server | Aurora PostgreSQL |
|---|---|---|
| Date and time | `DATEFIRST` | Use `DOW` in queries |
| Date and time | `DATEFORMAT` | `DateStyle` |
| Locking | `LOCK_TIMEOUT` | `lock_timeout` |
| Transactions | `IMPLICIT_TRANSACTIONS` | `SET TRANSACTION` |
| Transactions | `TRANSACTION ISOLATION LEVEL` | `BEGIN TRANSACTION ISOLATION LEVEL` |
| Query run | `IDENTITY_INSERT` | See Sequences and Identity |
| Query run | `LANGUAGE` | `lc_monetary`, `lc_numeric`, or `lc_time` |
| Query run | `QUOTED_IDENTIFIER` | N/A |
| Query run | `NOCOUNT` | N/A and not needed |
| Run stats | `SHOWPLAN_ALL`/`TEXT`/`XML`, `STATISTICS IO`/`PROFILE`/`TIME` | See Run Plans |
| Miscellaneous | `CONCAT_NULL_YIELDS_NULL` | N/A |
| Miscellaneous | `ROWCOUNT` | Use `LIMIT` within `SELECT` |

- Transaction isolation control maps closely; most other `SET` options differ significantly or have no equivalent.
- `SET ROWCOUNT` for DML must be rewritten to `TOP` (SQL Server) / `LIMIT` (PostgreSQL); not auto-convertible.
