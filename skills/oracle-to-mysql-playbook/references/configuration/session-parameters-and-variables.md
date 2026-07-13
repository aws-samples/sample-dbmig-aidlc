# Oracle Session Parameters and MySQL Session Variables

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.configuration.sessions.html

**Conversion category:** N/A (feature compatibility: one star)
**SCT automation:** N/A

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
| Time/date format | `ALTER SESSION SET nls_date_format = 'dd/mm/yyyy hh24:mi:ss';` | N/A |
| Current default schema/database | `ALTER SESSION SET current_schema='schema_name'` | N/A |
| Generate traces for specific errors | `ALTER SESSION SET events '10053 trace name context forever';` | N/A |
| Run trace for a SQL statement | `ALTER SESSION SET sql_trace=TRUE;` / `ALTER SYSTEM SET EVENTS 'sql_trace [sql:&&sql_id] bind=true, wait=true';` | `SET GLOBAL general_log = 'ON';` |
| Optimizer cost for index access | `ALTER SESSION SET optimizer_index_cost_adj = 50` | `SET SESSION optimizer_switch= ?` (see Switchable Optimizations) |
| Optimizer row access strategy | `ALTER SESSION SET optimizer_mode=all_rows;` | `SET SESSION optimizer_switch= ?` (see Switchable Optimizations) |
| Memory for sort operations | `ALTER SESSION SET sort_area_size=6321;` | `SET SESSION sort_buffer_size=32768;` |
| Memory for hash joins | `ALTER SESSION SET hash_area_size=1048576000;` | `SET SESSION join_buffer_size=1048576000;` |

## Conversion notes

- Several Oracle session settings have no MySQL equivalent: NLS date/language formats, `current_schema`, event-based tracing (`events '10053 ...'`). Handle NLS date formatting in application code or with explicit `DATE_FORMAT()` rather than a session parameter.
- Optimizer hints differ in model: Oracle uses scalar knobs (`optimizer_index_cost_adj`, `optimizer_mode`); MySQL toggles named strategies via `optimizer_switch`.
- Memory tuning maps roughly: `sort_area_size` → `sort_buffer_size`, `hash_area_size` → `join_buffer_size`.
- SQL tracing: Oracle's per-session `sql_trace` maps loosely to enabling MySQL's `general_log` (global), not a per-session equivalent.
- Time zone is set per session with `SET SESSION TIME_ZONE`, accepting offsets (`+10:00`) or named zones (`Europe/Helsinki`).
