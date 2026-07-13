# Single-row and Aggregate Functions

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.aggregate.html

**Conversion category:** Assisted (Four-star feature compatibility; not all functions are supported by PostgreSQL and some must be created manually)
**SCT automation:** Four-star automation level; SCT action code index N/A

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
| `REGEXP_SUBSTR` | `REGEXP_MATCHES` or `SUBSTRING` | No | `REGEXP_MATCHES('http://www.aws.com/products','(http://+./)') → {http://www.aws.com/}` |
| `REPLACE` | `REPLACE` | Yes | `replace('abcdef','abc','123') → 123def` |
| `LTRIM` / `RTRIM` | `LTRIM` / `RTRIM` | Yes | `ltrim('zzzyaws','xyz') → aws` |
| `SUBSTR` | `SUBSTRING` | No | `substring('John Smith', 6, 1) → S` |
| `TRIM` | `TRIM` | Partly | `trim(both from 'yxJohnxx','xyz') → John` |
| `ASCII` | `ASCII` | Yes | `ascii('a') → 97` |
| `INSTR` | N/A | No | Simulate using PostgreSQL built-in functions |
| `LENGTH` | `LENGTH` | Yes | `length('John S.') → 7` |
| `REGEXP_COUNT` | N/A | No | Available in Amazon Redshift if needed |
| `REGEXP_INSTR` | N/A | No | Available in Amazon Redshift if needed |

### Datetime functions

| Oracle | PostgreSQL | Equivalent | Notes / Example |
|---|---|---|---|
| `ADD_MONTHS` | N/A | No | Use `<date> + interval`: `now() + interval '1 month'` |
| `CURRENT_DATE` | `CURRENT_DATE` | Partly | PG `CURRENT_DATE` has no time; use `now()` / `current_timestamp` for time |
| `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP` | Yes | `select current_timestamp → 2017-01-01 13:01:01` |
| `EXTRACT (date part)` | `EXTRACT (date part)` | Yes | `EXTRACT(YEAR FROM DATE '2017-03-07') → 2017` |
| `LAST_DAY` | N/A | No | Redshift has it, or build a workaround in PG |
| `MONTHS_BETWEEN` | N/A | No | `DATE_PART('month', now()) - DATE_PART('month', now()- interval '100 days') → 3` |
| `SYSDATE` | `now()` | No | `select now() → 2017-01-01 13:01:01.123456+00` |
| `SYSTIMESTAMP` | `NOW()` | No | `select now()` includes fractional seconds + time zone |
| `LOCALTIMESTAMP` | `LOCALTIMESTAMP` | Yes | Current date/time in session time zone as TIMESTAMP |
| `TO_CHAR(datetime)` | `TO_CHAR(datetime)` | Yes | `TO_CHAR(now(),'DD-MON-YYYY HH24:MI:SS')` |
| `TRUNC (date)` | `DATE_TRUNC` | No | `date_trunc('day', now()) → 2017-01-01 00:00:00` |

### Encoding / decoding functions

| Oracle | PostgreSQL | Equivalent | Notes |
|---|---|---|---|
| `DECODE` | `DECODE` | No | PG `decode` decodes binary data from text; it is NOT Oracle's IF-THEN-ELSE. Use `CASE` instead |
| `DUMP` | N/A | No | No equivalent |
| `ORA_HASH` | N/A | No | No equivalent |

### Null functions

| Oracle | PostgreSQL | Equivalent | Notes / Example |
|---|---|---|---|
| `CASE` | `CASE` | Yes | `CASE WHEN condition THEN result [WHEN …] [ELSE result] END` |
| `COALESCE` | `COALESCE` | Yes | `coalesce(null,'a','b') → a` |
| `NULLIF` | `NULLIF` | Yes | `NULLIF('a','b') → a` |
| `NVL` | `COALESCE` | No | `coalesce(null,'a') → a` |
| `NVL2` | N/A | No | Use `CASE` instead |

### Environment / identifier functions

| Oracle | PostgreSQL | Equivalent | Notes / Example |
|---|---|---|---|
| `SYS_GUID` | `UUID_GENERATE_V1()` | No | `select uuid_generate_v1()` (requires uuid-ossp) |
| `UID` | N/A | No | Combine `current_user` with other built-ins |
| `USER` | `USER` / `SESSION_USER` / `CURRENT_USER` / `CURRENT_SCHEMA()` | No | `select user;` or `select current_schema();` |
| `USERENV` | N/A | No | See PG system functions docs |

### Conversion functions

| Oracle | PostgreSQL | Equivalent | Notes / Example |
|---|---|---|---|
| `CAST` | `CAST` | Yes | `cast('10' as int) + 1 → 11` |
| `CONVERT` | N/A | No | No equivalent (charset conversion) |
| `TO_CHAR (string/numeric)` | `TO_CHAR` | No | `select to_char(01234, '00000') → 01234` |
| `TO_DATE` | `TO_DATE` | Partly | `to_date('01Jan2017','DDMonYYYY') → 2017-01-01` |
| `TO_NUMBER` | `TO_NUMBER` | Partly | `to_number('01234','99999') → 1234` |

### Aggregate functions

| Oracle | PostgreSQL | Equivalent | Notes / Example |
|---|---|---|---|
| `AVG` | `AVG` | Yes | `select avg(salary) from employees` |
| `COUNT` | `COUNT` | Yes | `select count(*) from employees` |
| `LISTAGG` | `STRING_AGG` | No | `select string_agg(firstname, ' ,') from customer order by 1;` |
| `MAX` | `MAX` | Yes | `select max(salary) from employees` |
| `MIN` | `MIN` | Yes | `select min(salary) from employees` |
| `SUM` | `SUM` | Yes | `select sum(salary) from employees` |

### Top-N query

| Oracle | PostgreSQL | Equivalent | Example |
|---|---|---|---|
| `FETCH` | `FETCH` or `LIMIT` | Yes | `select * from customer fetch first 10 rows only` |

`REGEXP_MATCH` (introduced in PostgreSQL 10) example:

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
- `LISTAGG` → `STRING_AGG` (note ordering syntax differs: use `ORDER BY` outside, or within the aggregate).
- `SYS_GUID` → `uuid_generate_v1()` requires the `uuid-ossp` extension.
- Some Oracle functions (`REGEXP_COUNT`, `REGEXP_INSTR`, `LAST_DAY`) exist in Amazon Redshift but not core PostgreSQL — build workarounds for Aurora PostgreSQL.
