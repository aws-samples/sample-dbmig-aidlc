# Oracle and PostgreSQL Session Parameters

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.configuration.session.html

**Conversion category:** N/A (config topic) — feature compatibility: one star
**SCT automation:** N/A. Key difference: SET options are significantly different in PostgreSQL.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): `force_parallel_mode` → `debug_parallel_query`, plus timeouts, per-role defaults, and the `orafce.nls_date_format` scope.

## Oracle

Certain parameters are modifiable per-session with `ALTER SESSION`. Not all parameters are session-modifiable. List those that are:

```sql
SELECT NAME, VALUE FROM V$PARAMETER WHERE ISSES_MODIFIABLE='TRUE';
```

**Example — change the `NLS_LANGUAGE` codepage of the current session:**

```sql
alter session set nls_language='SPANISH';
-- Sesión modificada.
alter session set nls_language='ENGLISH';
-- Session altered.
alter session set nls_language='FRENCH';
-- Session modifiée.
alter session set nls_language='GERMAN';
-- Session wurde geändert.
```

**Example — set date format with `NLS_DATE_FORMAT`:**

```sql
select sysdate from dual;
-- SYSDATE
-- SEP-09-17

alter session set nls_date_format='DD-MON-RR';
select sysdate from dual;
-- 09-SEP-17

alter session set nls_date_format='MM-DD-YYYY';
select sysdate from dual;
-- 09-09-2017

alter session set nls_date_format='DAY-MON-RR';
```

## PostgreSQL

PostgreSQL configures session-modifiable parameters with `SET SESSION`; changes apply only to the current session. List parameters settable this way:

```sql
SELECT * FROM pg_settings where context = 'user';
```

Commonly used session parameters:
* `client_encoding` — configures the connected client character set
* `debug_parallel_query` — forces use of parallel query for the session (testing only). PostgreSQL 16 renamed it from `force_parallel_mode`, which no longer exists; verified on Aurora PostgreSQL 18.6.
* `lock_timeout` — max duration to wait for a database lock to release
* `statement_timeout`, `transaction_timeout` (PG 17+), `idle_in_transaction_session_timeout` — per-statement, per-transaction and idle-in-transaction limits
* `search_path` — schema search order for non-schema-qualified object names
* `transaction_isolation` — current Transaction Isolation Level for the session

**Example — change the date style of the connected session:**

```sql
set session DateStyle to POSTGRES, DMY;
SET
select now();
-- now
-- Sat 09 Sep 11:03:43.597202 2017 UTC
-- (1 row)

set session DateStyle to ISO, MDY;
SET
select now();
-- now
-- 2017-09-09 11:04:01.3859+00
-- (1 row)
```

## Conversion notes

Partial mapping of session-level parameters (not all are directly comparable):

| Parameter purpose | Oracle | PostgreSQL |
|---|---|---|
| Configure time and date format | `ALTER SESSION SET nls_date_format = 'dd/mm/yyyy hh24:mi:ss';` | `SET SESSION datestyle to 'SQL, DMY';` |
| Configure current default schema/database | `ALTER SESSION SET current_schema='schema_name'` | `SET SESSION SEARCH_PATH TO schemaname;` |
| Generate traces for specific errors | `ALTER SESSION SET events '10053 trace name context forever';` | N/A |
| Run trace for a SQL statement | `ALTER SESSION SET sql_trace=TRUE;` / `ALTER SYSTEM SET EVENTS 'sql_trace [sql:&&sql_id] bindd=true, wait=true';` | N/A |
| Modify optimizer cost for index access | `ALTER SESSION SET optimizer_index_cost_adj = 50` | `SET SESSION random_page_cost TO 6;` |
| Modify optimizer row access strategy | `ALTER SESSION SET optimizer_mode=all_rows;` | N/A |
| Memory allocated to sort operations | `ALTER SESSION SET sort_area_size=6321;` | `SET SESSION work_mem TO '6MB';` |
| Memory allocated to hash joins | `ALTER SESSION SET hash_area_size=1048576000;` | `SET SESSION work_mem TO '6MB';` |

- Oracle separates sort vs hash memory (`sort_area_size`, `hash_area_size`); PostgreSQL consolidates both into `work_mem`.
- Oracle tracing/event facilities (`10053`, `sql_trace`) have no PostgreSQL session-parameter equivalent.
- Use `SET SESSION` for session scope; `SET LOCAL` for transaction scope; `RESET <param>` to restore defaults.

### Aurora PostgreSQL 18 notes (validated on 18.6)

- **Make session settings persistent per user or database** instead of relying on a logon trigger: `ALTER ROLE app_user SET search_path = app, public;` or `ALTER DATABASE appdb SET datestyle = 'ISO, DMY';`. This replaces most Oracle `AFTER LOGON` triggers that run `ALTER SESSION`. For logon logic that needs code, PostgreSQL 17+ has `CREATE EVENT TRIGGER … ON login` (verified on Aurora 18.6 as the master user). A failing login trigger blocks every connection, so keep it trivial and exception-safe.
- `datestyle` affects only output and input parsing, so it is not a full replacement for `NLS_DATE_FORMAT`. Converted code should format dates explicitly with `to_char(…, 'DD-MON-YYYY')` and not depend on session settings. `lc_time` controls localized month/day names in `to_char` with the `TM` prefix.
- With the `orafce` extension (version 4.16 on Aurora 18), `orafce.nls_date_format` sets the default format used by orafce's Oracle-compatible `oracle.date` functions. It does not change native PostgreSQL `date`/`timestamp` output.
- Oracle `ALTER SESSION SET TIME_ZONE` → `SET TIME ZONE 'Europe/Paris'` (or `SET timezone`). The Aurora default is `UTC`.
- Oracle `sql_trace` / 10046 tracing: use `auto_explain` (preloadable in Aurora 18) with `auto_explain.log_min_duration`, plus `pg_stat_statements`. Neither captures waits like a 10046 trace; use CloudWatch Database Insights for wait analysis.
