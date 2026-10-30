# Timezone Data Types and CONVERT_TZ

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.timezone.html

**Conversion category:** Manual (★★ feature compatibility, no automation)
**SCT automation:** Action code "Date and Time Functions" — no equivalent for `CREATE TABLE…TIMESTAMP WITH TIME ZONE`; use `CONVERT_TZ`.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Aurora facts (system zone UTC, set time_zone in the cluster parameter group, named zones pre-loaded — verified), TIMESTAMP 2038 limit (verified), offset literals, toolkit datatype mapping, UTC_TIMESTAMP.

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

MySQL has time zone functions similar to Oracle but far fewer options — most functionality works in **queries, not DDL**. **No equivalent** for Oracle `CREATE TABLE…TIMESTAMP WITH TIME ZONE`.

On Aurora MySQL 3 and 8.4 (verified): `system_time_zone` is **UTC** and `time_zone` is `SYSTEM`; change the server zone with the `time_zone` parameter in the DB cluster parameter group (there is no OS `TZ` to set), or per session with `SET time_zone = 'Europe/Paris'`. Named time-zone tables are **pre-loaded** (`mysql.time_zone_name` has ~1,790 entries), so `CONVERT_TZ('…', 'UTC', 'Europe/Paris')` works without `mysql_tzinfo_to_sql` (verified).

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
- Named zones work out of the box on Aurora (see above); `mysql_tzinfo_to_sql` is not needed.
- **`TIMESTAMP` vs `DATETIME`:** `TIMESTAMP` stores UTC and converts from/to the session `time_zone`; its range ends at **2038-01-19 03:14:07 UTC** (inserting `2038-01-20` fails with error 1292, verified). `DATETIME` stores the value as given with no zone. For Oracle `TIMESTAMP WITH TIME ZONE`, store UTC in `DATETIME(6)` plus, if the original offset matters, a separate `VARCHAR(6)` offset or zone-name column. The toolkit's datatype map uses `datetime(p)` for `WITH TIME ZONE` and `timestamp(p)` for `WITH LOCAL TIME ZONE` — check `WITH LOCAL TIME ZONE` columns against the 2038 limit.
- Literals with an offset (`'2024-06-01 12:00:00+02:00'`, MySQL 8.0.19+) are converted to the session time zone on insert into both `TIMESTAMP` and `DATETIME` (verified: stored as `10:00:00` in a UTC session); the offset itself is not stored.
- `SYSTIMESTAMP`/`CURRENT_TIMESTAMP` in Oracle carry a zone; MySQL `NOW()` returns session-zone local time. Use `UTC_TIMESTAMP(6)` where Oracle code called `SYS_EXTRACT_UTC(SYSTIMESTAMP)`.
- Migrate Oracle `WITH TIME ZONE`/`WITH LOCAL TIME ZONE` columns to plain `TIMESTAMP`/`DATETIME` plus application-level or `CONVERT_TZ` conversion.
