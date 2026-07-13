# Timezone Data Types and CONVERT_TZ

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.timezone.html

**Conversion category:** Manual (★★ feature compatibility, no automation)
**SCT automation:** Action code "Date and Time Functions" — no equivalent for `CREATE TABLE…TIMESTAMP WITH TIME ZONE`; use `CONVERT_TZ`.

## Oracle

`TIMESTAMP` variants:
* `TIMESTAMP WITH LOCAL TIME ZONE` — stored normalized to DB time zone (offset not stored); returned in the user's session time zone.
* `TIMESTAMP WITH TIME ZONE` — stores a time zone offset or region name (13 bytes; 2 more than LOCAL).

Best practice: use `TIMESTAMP WITH TIME ZONE` for cross-time-zone apps.

Time zone functions:
| Function | Description |
|---|---|
| `NEW_TIME` | Convert date/time from one time zone to another |
| `FROM_TZ` | Convert a TZ to `TIMESTAMP WITH TIME ZONE` |
| `CURRENT_TIMESTAMP` | Current date/time in session time zone |
| `DBTIMEZONE` | Current date/time in database time zone |
| `SYS_EXTRACT_UTC` | UTC date/time |
| `TO_TIMESTAMP_TZ` | Convert string to `TIMESTAMP WITH TIME ZONE` |

```sql
-- TIMESTAMP WITH LOCAL TIME ZONE
CREATE TABLE tz_local (id NUMBER, tz_col TIMESTAMP WITH LOCAL TIME ZONE);
INSERT INTO tz_local VALUES(1, '01-JAN-2018 2:00:00');
INSERT INTO tz_local VALUES(2, TIMESTAMP '2018-01-01 2:00:00');
INSERT INTO tz_local VALUES(3, TIMESTAMP '2018-01-01 2:00:00 -08:00');
-- row 3 displays as 2018-01-01 05:00:00 (converted to local)

-- TIMESTAMP WITH TIME ZONE
ALTER SESSION SET TIME_ZONE='-4:00';
CREATE TABLE tz_tbl (id NUMBER, tz_col TIMESTAMP WITH TIME ZONE);
INSERT INTO tz_tbl VALUES(1, '01-JAN-2018 2:00:00 AM -5:00');
INSERT INTO tz_tbl VALUES(2, TIMESTAMP '2018-01-01 3:00:00');
INSERT INTO tz_tbl VALUES(3, TIMESTAMP '2018-01-01 2:00:00 -8:00');
```

## MySQL

MySQL has time zone functions similar to Oracle but far fewer options — most functionality works in **queries, not DDL**. At startup the host time zone is placed in `system_time_zone` (modifiable via the OS `TZ` environment variable). **No equivalent** for Oracle `CREATE TABLE…TIMESTAMP WITH TIME ZONE`.

```sql
-- Query global and session time zone
SELECT @@global.time_zone, @@session.time_zone;
-- SYSTEM    Europe/Moscow
```

## Conversion notes

| Oracle function | MySQL |
|---|---|
| `NEW_TIME` | `CONVERT_TZ` (must specify source time zone) |
| `FROM_TZ` | `CONVERT_TZ` |
| `DBTIMEZONE` | `CONVERT_TZ(CURRENT_TIME(),@@global.time_zone,@@global.time_zone)` |
| `SYS_EXTRACT_UTC` | `CONVERT_TZ(CURRENT_TIME(),@@global.time_zone,'+00:00')` |
| `TO_TIMESTAMP_TZ` | `CONVERT_TZ(STR_TO_DATE('17-09-2010 23:15','%d-%m-%Y %H:%i'),@@global.time_zone,'+03:00')` |

- There is no time-zone-aware column type — store UTC (or a fixed zone) in `TIMESTAMP`/`DATETIME` and apply `CONVERT_TZ` at query time.
- `CONVERT_TZ` requires named-zone tables to be loaded (`mysql_tzinfo_to_sql`) if using region names instead of numeric offsets.
- Migrate Oracle `WITH TIME ZONE`/`WITH LOCAL TIME ZONE` columns to plain `TIMESTAMP`/`DATETIME` plus application-level or `CONVERT_TZ` conversion.
