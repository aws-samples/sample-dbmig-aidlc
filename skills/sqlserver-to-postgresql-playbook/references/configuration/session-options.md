# Configuring Session Options

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.configuration.sessionoptions.html

**Conversion category:** N/A (Two-star feature compatibility)
**SCT automation:** N/A — `SET ROWCOUNT` for DML cannot be converted automatically; SCT can convert `SET ROWCOUNT`→`TOP` patterns automatically when already rewritten.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): `debug_parallel_query` (verified), fixed the batch-delete loop (verified), corrected `IMPLICIT_TRANSACTIONS`/`XACT_ABORT`/`DATEFIRST` mappings, per-routine `SET`.

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
  SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;   -- the playbook's TRANSACTION_ISOLATION_LEVEL is a typo
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
- `debug_parallel_query` — forces parallel query for the session (testing only; PG 16 renamed it from `force_parallel_mode`, which no longer exists, verified on 18.6).
- `statement_timeout`, `transaction_timeout` (PG 17+), `idle_in_transaction_session_timeout` — runtime limits.
- `lock_timeout` — max duration to wait for a database lock to release.
- `search_path` — schema search order for non-schema-qualified object names.
- `transaction_isolation` — current transaction isolation level for the session.

View variables via the psql command line, Aurora cluster/instance parameters, or system variable interfaces.

**Converting `SET ROWCOUNT` for DML:** Code using `SET ROWCOUNT` cannot be converted automatically. Rewrite to `TOP` before running SCT, or change manually afterward. The `TOP`-batched delete maps to a `LIMIT`-based loop:

```sql
-- (the playbook's original example used a non-existent row_count() function; this form is verified on 18.6)
DO $$
DECLARE n int;
BEGIN
  LOOP
    DELETE FROM num_test
     WHERE ctid IN (SELECT ctid FROM num_test WHERE for_delete LIMIT 5000);
    GET DIAGNOSTICS n = ROW_COUNT;      -- ≈ @@ROWCOUNT
    EXIT WHEN n = 0;
    COMMIT;                             -- allowed in DO/procedures (PG 11+), releases locks between batches
  END LOOP;
END $$;
```
Prefer a key range (`WHERE id IN (SELECT id … LIMIT 5000)`) over `ctid` when the table has a primary key.

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
| Date and time | `DATEFIRST` | No setting. Use `extract(isodow …)` (Monday = 1, matches `DATEFIRST 1`) or `extract(dow …)` (Sunday = 0); verified |
| Date and time | `DATEFORMAT` | `DateStyle` (input parsing) — prefer ISO literals and explicit `to_date`/`to_timestamp` |
| Locking | `LOCK_TIMEOUT` | `lock_timeout` |
| Locking | `DEADLOCK_PRIORITY` | No equivalent; PostgreSQL picks the victim |
| Transactions | `IMPLICIT_TRANSACTIONS ON` | Client autocommit off (driver/`psql` setting); there is no server switch |
| Transactions | `TRANSACTION ISOLATION LEVEL` | `SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL …` or `BEGIN ISOLATION LEVEL …` |
| Transactions | `XACT_ABORT ON` | Always on in effect: any error aborts the current transaction in PostgreSQL |
| Miscellaneous | `CONCAT_NULL_YIELDS_NULL ON` | Default PostgreSQL `\|\|` behavior; for `OFF` semantics use `concat()` |
| Miscellaneous | `ANSI_NULLS`, `ANSI_PADDING`, `ANSI_WARNINGS`, `ARITHABORT` | Always standard; drop |
| Query run | `IDENTITY_INSERT` | See Sequences and Identity |
| Query run | `LANGUAGE` | `lc_monetary`, `lc_numeric`, or `lc_time` |
| Query run | `QUOTED_IDENTIFIER` | N/A |
| Query run | `NOCOUNT` | N/A and not needed |
| Run stats | `SHOWPLAN_ALL`/`TEXT`/`XML`, `STATISTICS IO`/`PROFILE`/`TIME` | See Run Plans |
| Miscellaneous | `CONCAT_NULL_YIELDS_NULL` | N/A |
| Miscellaneous | `ROWCOUNT` | Use `LIMIT` within `SELECT` |

- Transaction isolation control maps closely; most other `SET` options differ significantly or have no equivalent.
- `SET ROWCOUNT` for DML must be rewritten to `TOP` (SQL Server) / `LIMIT` (PostgreSQL); not auto-convertible.
- Settings a procedure needs every time → `ALTER FUNCTION/PROCEDURE … SET param = value` (scoped to the call, like SQL Server's per-module saved settings) or `ALTER ROLE … SET`.
