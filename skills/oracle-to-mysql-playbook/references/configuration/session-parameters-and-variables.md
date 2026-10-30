# Oracle Session Parameters and MySQL Session Variables

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.configuration.sessions.html

**Conversion category:** N/A (feature compatibility: one star)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): USE for current_schema, optimizer_trace for 10053 (verified), lc_time_names (verified), SET GLOBAL denied to the master user (verified), connection-init and RDS Proxy pinning guidance.

**Key difference:** `SET` options are significantly different.

## Oracle

Many Oracle parameters are modifiable per session with `ALTER SESSION`. List session-modifiable parameters:

```sql
SELECT NAME, VALUE FROM V$PARAMETER WHERE ISSES_MODIFIABLE='TRUE';
```

### Examples

```sql
ALTER SESSION SET nls_language='SPANISH';
ALTER SESSION SET nls_language='ENGLISH';

SELECT sysdate FROM dual;            -- SEP-09-17
ALTER SESSION SET nls_date_format='DD-MON-RR';
SELECT sysdate FROM dual;            -- 09-SEP-17
ALTER SESSION SET nls_date_format='MM-DD-YYYY';
SELECT sysdate FROM dual;            -- 09-09-2017
```

## MySQL

MySQL configures session-modifiable variables with `SET SESSION`; the change applies only to the current session. (See "Dynamic System Variables" for variables with session scope.)

Commonly used session variables:

- `autocommit` — whether changes take effect immediately or require explicit `COMMIT`
- `character_set_client` — client character set
- `default_storage_engine` — default storage engine
- `foreign_key_checks` — whether to run FK checks
- `innodb_lock_wait_timeout` — time a transaction waits to acquire a row lock

### Example

```sql
SELECT now();                        -- 2018-02-26 12:13:25
SET SESSION TIME_ZONE = '+10:00';
SELECT now();                        -- 2018-02-26 22:14:03
```

A time zone name such as `Europe/Helsinki` may be used instead of `+10:00`.

## Oracle and MySQL session parameter examples

| Purpose | Oracle | MySQL |
|---|---|---|
| Time/date format | `ALTER SESSION SET nls_date_format = 'dd/mm/yyyy hh24:mi:ss';` | N/A — use explicit `DATE_FORMAT()` |
| Date language | `ALTER SESSION SET nls_date_language = 'GERMAN'` | `SET SESSION lc_time_names = 'de_DE'` (verified: `Mittwoch 01. Mai 2024`) |
| Current default schema/database | `ALTER SESSION SET current_schema='schema_name'` | `USE schema_name;` (sets the default database; affects unqualified names only) |
| Optimizer trace (event 10053) | `ALTER SESSION SET events '10053 trace name context forever';` | `SET SESSION optimizer_trace = 'enabled=on';` then `SELECT trace FROM information_schema.optimizer_trace` (verified) |
| Run trace for a SQL statement | `ALTER SESSION SET sql_trace=TRUE;` / `ALTER SYSTEM SET EVENTS 'sql_trace [sql:&&sql_id] bind=true, wait=true';` | `EXPLAIN ANALYZE <stmt>` for one statement; `general_log`/`slow_query_log` + `long_query_time = 0` in the parameter group for all statements. `SET GLOBAL general_log = 'ON'` is denied to the Aurora master user (error 1227, verified) |
| Optimizer cost for index access | `ALTER SESSION SET optimizer_index_cost_adj = 50` | `SET SESSION optimizer_switch= ?` (see Switchable Optimizations) |
| Optimizer row access strategy | `ALTER SESSION SET optimizer_mode=all_rows;` | `SET SESSION optimizer_switch= ?` (see Switchable Optimizations) |
| Memory for sort operations | `ALTER SESSION SET sort_area_size=6321;` | `SET SESSION sort_buffer_size=32768;` |
| Memory for hash joins | `ALTER SESSION SET hash_area_size=1048576000;` | `SET SESSION join_buffer_size=1048576000;` |

## Conversion notes

- Several Oracle session settings have no MySQL equivalent: NLS date formats and numeric characters. Handle NLS date formatting in application code or with explicit `DATE_FORMAT()`. `current_schema` → `USE`, 10053 → `optimizer_trace`, `nls_date_language` → `lc_time_names` (see table).
- `SET GLOBAL …` is not available to the Aurora master user for most variables (error 1227 for `general_log` and `transaction_isolation`, verified); instance-wide changes go through parameter groups.
- Session settings that converted code depends on (`sql_mode`, `time_zone`, `transaction_isolation`, `group_concat_max_len`) should be set by the application's connection initialization (`init_command` / driver option), not per procedure. Each `SET` makes RDS Proxy pin the connection.
- Optimizer hints differ in model: Oracle uses scalar knobs (`optimizer_index_cost_adj`, `optimizer_mode`); MySQL toggles named strategies via `optimizer_switch`.
- Memory tuning maps roughly: `sort_area_size` → `sort_buffer_size`, `hash_area_size` → `join_buffer_size`.
- SQL tracing: Oracle's per-session `sql_trace` maps loosely to the global `general_log` (parameter group). Per-statement detail comes from `EXPLAIN ANALYZE` and, with `performance_schema` ON, `events_statements_history`.
- Time zone is set per session with `SET SESSION TIME_ZONE`, accepting offsets (`+10:00`) or named zones (`Europe/Helsinki`).
