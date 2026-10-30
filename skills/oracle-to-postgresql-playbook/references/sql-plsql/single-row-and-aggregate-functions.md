# Single-row and Aggregate Functions

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.aggregate.html

**Conversion category:** Assisted (Four-star feature compatibility; not all functions are supported by PostgreSQL and some must be created manually)
**SCT automation:** Four-star automation level; SCT action code index N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PG 15 regex functions are native (verified); negative `SUBSTR`, `ADD_MONTHS` month-end, `TO_DATE` time loss, `SYSDATE` transaction-start semantics, empty-string vs NULL (all verified); orafce equivalents; corrected `MONTHS_BETWEEN`; `gen_random_uuid`/`uuidv7` for `SYS_GUID`.

## Oracle

Oracle provides two main categories of built-in SQL functions:

- **Single-row (scalar) functions** return one result per row. Usable in `SELECT`, `WHERE`, `START WITH`, `CONNECT BY`, and `HAVING`. Grouped by data type: NUMERIC, CHAR, DATETIME, etc.
- **Aggregate (group) functions** summarize a group of values into a single result: `AVG`, `MIN`, `MAX`, `SUM`, `COUNT`, `LISTAGG`, `FIRST`, `LAST`.

Oracle 19c additions:
- `LISTAGG` supports `DISTINCT` to eliminate duplicates.
- New bitmap aggregate functions (`BITMAP_BUCKET_NUMBER`, `BITMAP_BIT_POSITION`, `BITMAP_CONSTRUCT_AGG`) speed up `COUNT DISTINCT`.

## PostgreSQL

PostgreSQL provides an extensive set of single-row and aggregate functions. Some match Oracle by name and behavior; some have different names but equivalent behavior; some share a name but behave differently. The "Equivalent" column below indicates functional equivalency.

### Numeric functions (all equivalent: Yes)

| Oracle | PostgreSQL | Example |
|---|---|---|
| `ABS` | `ABS(n)` | `abs(-11.3) → 11.3` |
| `CEIL` | `CEIL` / `CEILING` | `ceil(-24.9) → -24` |
| `FLOOR` | `FLOOR` | `floor(-43.7) → -44` |
| `MOD` | `MOD` | `mod(10,3) → 1` |
| `ROUND` | `ROUND` | `round(3.49, 1) → 3.5` |
| `TRUNC (Number)` | `TRUNC (Number)` | `trunc(13.5) → 13` |

### Character functions

| Oracle | PostgreSQL | Equivalent | Notes / Example |
|---|---|---|---|
| `CONCAT` | `CONCAT` | Partly | PG `concat` concatenates text of all args: `concat('a', 1) → a1` |
| `LOWER` / `UPPER` | `LOWER` / `UPPER` | Yes | `lower('MR. Smith') → mr. smith` |
| `LPAD` / `RPAD` | `LPAD` / `RPAD` | Yes | `LPAD('Log-1',10,'-') → -----Log-1` |
| `REGEXP_REPLACE` | `REGEXP_REPLACE` | Yes | `regexp_replace('John','[hn].','1') → Jo1` |
| `REGEXP_SUBSTR` | `REGEXP_SUBSTR` (PG 15+) | Yes | `regexp_substr('aXbYc','[XY]',1,2) → Y` (verified) |
| `REGEXP_LIKE` | `REGEXP_LIKE` (PG 15+) | Yes | `regexp_like('Hello','^h','i') → true` (verified) |
| `REPLACE` | `REPLACE` | Yes | `replace('abcdef','abc','123') → 123def` |
| `LTRIM` / `RTRIM` | `LTRIM` / `RTRIM` | Yes | `ltrim('zzzyaws','xyz') → aws` |
| `SUBSTR` | `SUBSTR` / `SUBSTRING` | Partly | Same for positive positions. **Negative start differs:** Oracle `substr('abcdef',-2) → 'ef'`, PostgreSQL `substr('abcdef',-2) → 'abcdef'` (verified). Use `right(s, 2)` or orafce `oracle.substr()` |
| `TRIM` | `TRIM` | Partly | `trim(both from 'yxJohnxx','xyz') → John` |
| `ASCII` | `ASCII` | Yes | `ascii('a') → 97` |
| `INSTR` | `strpos(s, sub)` / `position(sub IN s)` (first occurrence); `regexp_instr` (PG 15+) or orafce `oracle.instr(s, sub, pos, occurrence)` for position/occurrence | Partly | `oracle.instr('aXbXc','X',1,2) → 4` (verified) |
| `LENGTH` | `LENGTH` | Partly | `length('') → 0` in PostgreSQL but `NULL` in Oracle (empty string is NULL there). `LENGTHB` → `octet_length` |
| `REGEXP_COUNT` | `REGEXP_COUNT` (PG 15+) | Yes | `regexp_count('aXbXc','X') → 2` (verified) |
| `REGEXP_INSTR` | `REGEXP_INSTR` (PG 15+) | Yes | `regexp_instr('aXbXc','X',1,2) → 4` (verified) |
| `INITCAP`, `TRANSLATE`, `REVERSE` | same | Yes | (verified) |

### Datetime functions

| Oracle | PostgreSQL | Equivalent | Notes / Example |
|---|---|---|---|
| `ADD_MONTHS` | orafce `oracle.add_months` / `+ interval 'n month'` | Partly | **End-of-month differs:** Oracle maps a last-day-of-month input to the last day of the result month. `date '2024-02-29' + interval '1 month' → 2024-03-29`, while `oracle.add_months(date '2024-02-29', 1) → 2024-03-31` (Oracle behavior, verified). Use orafce where month-end logic matters |
| `CURRENT_DATE` | `CURRENT_DATE` | Partly | PG `CURRENT_DATE` has no time; use `now()` / `current_timestamp` for time |
| `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP` | Yes | `select current_timestamp → 2017-01-01 13:01:01` |
| `EXTRACT (date part)` | `EXTRACT (date part)` | Yes | `EXTRACT(YEAR FROM DATE '2017-03-07') → 2017` |
| `LAST_DAY` | orafce `oracle.last_day` or `(date_trunc('month', d) + interval '1 month - 1 day')::date` | Yes | `→ 2024-02-29` (both verified) |
| `MONTHS_BETWEEN` | orafce `oracle.months_between(d1, d2)` | Yes (orafce) | `oracle.months_between(date '2024-03-31', date '2024-01-15') → 2.516…` (verified). The old `DATE_PART('month', …)` subtraction is **wrong** across years and day fractions; do not use it |
| `SYSDATE` | `LOCALTIMESTAMP(0)` or `clock_timestamp()::timestamp(0)` | Partly | `now()`/`LOCALTIMESTAMP` are fixed at **transaction start**; Oracle `SYSDATE` advances within a transaction. Use `clock_timestamp()` where code measures elapsed time. `now()` returns `timestamptz` (verified) |
| `SYSTIMESTAMP` | `CURRENT_TIMESTAMP` / `clock_timestamp()` | Partly | Returns `timestamptz`, with the same transaction-start caveat |
| Date subtraction | `d1 - d2` | Partly | `date - date → integer` days; `timestamp - timestamp → interval` (`'9 days 12:00:00'`, verified). Oracle returns a fractional number of days; use `extract(epoch from t1 - t2)/86400` |
| `LOCALTIMESTAMP` | `LOCALTIMESTAMP` | Yes | Current date/time in session time zone as TIMESTAMP |
| `TO_CHAR(datetime)` | `TO_CHAR(datetime)` | Yes | `TO_CHAR(now(),'DD-MON-YYYY HH24:MI:SS')` |
| `TRUNC (date)` | `DATE_TRUNC` / orafce `oracle.trunc(d, 'MM')` | Partly | `date_trunc('month', d)` returns `timestamp`; cast to `date` if needed. orafce accepts Oracle format models (`'MM'`, `'Q'`, `'IW'`) (verified) |

### Encoding / decoding functions

| Oracle | PostgreSQL | Equivalent | Notes |
|---|---|---|---|
| `DECODE` | `CASE` (or orafce `oracle.decode`) | No | PG `decode` decodes binary data from text; it is NOT Oracle's IF-THEN-ELSE. Use `CASE` (preferred), or `oracle.decode(1,1,'one','other')` (verified). Oracle `DECODE` treats `NULL = NULL` as a match; `CASE x WHEN NULL` does not, so use `CASE WHEN x IS NULL THEN …` |
| `DUMP` | N/A | No | No equivalent (`pg_column_size`, `encode(…, 'hex')` for inspection) |
| `ORA_HASH` / `STANDARD_HASH` | `hashtext()` (32-bit, not stable across major versions); `md5()`, `sha256()` (PG 11+) | Partly | Values differ from Oracle. Do not compare hashes across engines |

### Null functions

| Oracle | PostgreSQL | Equivalent | Notes / Example |
|---|---|---|---|
| `CASE` | `CASE` | Yes | `CASE WHEN condition THEN result [WHEN …] [ELSE result] END` |
| `COALESCE` | `COALESCE` | Yes | `coalesce(null,'a','b') → a` |
| `NULLIF` | `NULLIF` | Yes | `NULLIF('a','b') → a` |
| `NVL` | `COALESCE` | No | `coalesce(null,'a') → a` |
| `NVL2` | `CASE WHEN x IS NOT NULL THEN a ELSE b END` (or orafce `oracle.nvl2`) | Yes | (verified) |

### Environment / identifier functions

| Oracle | PostgreSQL | Equivalent | Notes / Example |
|---|---|---|---|
| `SYS_GUID` | `gen_random_uuid()` (core) or `uuidv7()` (PG 18, time-ordered) | Partly | Returns `uuid`, not `RAW(16)`. Store keys as `uuid`. `uuid-ossp` is no longer needed |
| `UID` | N/A | No | `(SELECT oid FROM pg_roles WHERE rolname = current_user)` if a number is really needed |
| `USER` | `USER` / `SESSION_USER` / `CURRENT_USER` / `CURRENT_SCHEMA()` | Partly | Role names are lower-case unless created quoted |
| `USERENV` / `SYS_CONTEXT('USERENV', …)` | `session_user`, `current_schema()`, `current_database()`, `inet_client_addr()`, `pg_backend_pid()`, `current_setting('application_name')` | Partly | Custom application contexts (`DBMS_SESSION.SET_CONTEXT`) → `set_config('app.key', v, false)` / `current_setting('app.key', true)` |

### Conversion functions

| Oracle | PostgreSQL | Equivalent | Notes / Example |
|---|---|---|---|
| `CAST` | `CAST` | Yes | `cast('10' as int) + 1 → 11` |
| `CONVERT` | `convert_to(text, 'LATIN1')` / `convert_from(bytea, enc)` | Partly | Works on `bytea` (verified) |
| `TO_CHAR (string/numeric)` | `TO_CHAR` | No | `select to_char(01234, '00000') → 01234` |
| `TO_DATE` | `TO_TIMESTAMP(…)::timestamp(0)` (keeps time) / `TO_DATE` (date only) | Partly | **PG `to_date` drops the time part** (`to_date('2024-01-15 13:45:00', 'YYYY-MM-DD HH24:MI:SS') → 2024-01-15`, verified). Oracle `DATE` has a time, so map `TO_DATE` to `to_timestamp` whenever the target column is `timestamp(0)` |
| `TO_NUMBER` | `TO_NUMBER` | Partly | `to_number('01234','99999') → 1234` |

### Aggregate functions

| Oracle | PostgreSQL | Equivalent | Notes / Example |
|---|---|---|---|
| `AVG` | `AVG` | Yes | `select avg(salary) from employees` |
| `COUNT` | `COUNT` | Yes | `select count(*) from employees` |
| `LISTAGG` | `STRING_AGG` | Yes (rewrite) | `LISTAGG(x, ',') WITHIN GROUP (ORDER BY x)` → `string_agg(x, ',' ORDER BY x)`; `LISTAGG(DISTINCT …)` → `string_agg(DISTINCT x, ',' ORDER BY x)` (verified). The `ORDER BY` goes **inside** the aggregate |
| `ANY_VALUE` | `ANY_VALUE` (PG 16+) | Yes | (verified) |
| `MAX` | `MAX` | Yes | `select max(salary) from employees` |
| `MIN` | `MIN` | Yes | `select min(salary) from employees` |
| `SUM` | `SUM` | Yes | `select sum(salary) from employees` |

### Top-N query

| Oracle | PostgreSQL | Equivalent | Example |
|---|---|---|---|
| `FETCH` | `FETCH` or `LIMIT` | Yes | `select * from customer fetch first 10 rows only` |

`REGEXP_MATCH` (PostgreSQL 10+) returns the capture groups as an array:

```sql
SELECT REGEXP_MATCH('foobarbequebaz','bar.*que');
 regexp_match
-------------
 {barbeque}
```

## Conversion notes

- Most numeric and basic aggregate functions map 1:1 and convert automatically.
- Watch out for functions that share a name but differ in behavior: **`DECODE`** (binary decode in PG, not IF-THEN-ELSE) and **`CONCAT`**/**`SUBSTR`**/**`TRIM`** (partial equivalency).
- `NVL` → `COALESCE`; `NVL2` → `CASE`.
- Date arithmetic: replace `ADD_MONTHS`, `MONTHS_BETWEEN`, `LAST_DAY`, `SYSDATE`, `SYSTIMESTAMP`, `TRUNC(date)` with `interval` math, `now()`, and `date_trunc`.
- `LISTAGG` → `STRING_AGG` with the `ORDER BY` **inside** the aggregate call.
- `SYS_GUID` → `gen_random_uuid()` or `uuidv7()` (PG 18). No extension needed.
- **Oracle regex functions are native since PG 15**: `REGEXP_LIKE`, `REGEXP_COUNT`, `REGEXP_INSTR`, `REGEXP_SUBSTR` (verified on 18.6), plus `REGEXP_REPLACE`. Most Oracle regex calls convert unchanged. Check flags (`'i'`, `'c'`, `'n'`, `'m'`) and back-references.
- `LAST_DAY`, `MONTHS_BETWEEN`, `ADD_MONTHS` (month-end semantics), `NVL2`, `DECODE`, `INSTR` with occurrence, and negative `SUBSTR` are all in **orafce** (`oracle` schema, verified). Use orafce or the native rewrites above; never the `DATE_PART('month')` subtraction for `MONTHS_BETWEEN`.
- **Empty string vs NULL**: Oracle treats `''` as NULL, PostgreSQL does not (`length('') = 0`, `'' IS NULL` is false, verified). Review `NVL(col, '')`, `col = ''`, and `LENGTH(col) IS NULL` checks in converted code.
