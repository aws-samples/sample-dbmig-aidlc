# Single-row and Aggregate Functions

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.aggregate.html

**Conversion category:** Assisted (★★★★ feature compatibility, ★★★★ automation)
**SCT automation:** N/A — MySQL doesn't support all functions; unsupported functions require manual creation.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected mappings now native on MySQL 8 (REGEXP_*), TRUNCATE needs 2 args, LENGTH counts bytes (use CHAR_LENGTH), SUBSTR position 0, TRIM(LEADING) vs char sets, ADD_MONTHS/MONTHS_BETWEEN month-end differences, DECODE NULL semantics, FETCH FIRST not supported, GROUP_CONCAT truncation, CAST target types, %b format — all verified on both versions.

## Oracle

Oracle provides two main categories of built-in SQL functions:
* **Single-row (scalar) functions** return one result per row. Usable in `SELECT`, `WHERE`, `START WITH`, `CONNECT BY`, and `HAVING`. Grouped by datatype (`NUMERIC`, `CHAR`, `DATETIME`).
* **Aggregate (group) functions** summarize a group of values into a single result: `AVG`, `MIN`, `MAX`, `SUM`, `COUNT`, `LISTAGG`, `FIRST`, `LAST`.

Oracle 19c adds `DISTINCT` keyword to `LISTAGG`, and bitmap aggregates `BITMAP_BUCKET_NUMBER`, `BITMAP_BIT_POSITION`, `BITMAP_CONSTRUCT_AGG` (speed up `COUNT DISTINCT`).

```sql
SELECT avg(salary) FROM employees;
SELECT listagg(firstname,' ,') within group (order by customerid) FROM customer;
```

## MySQL

MySQL offers extensive single-row and aggregate functions. Many match Oracle by name and behavior; some differ.

```sql
SELECT avg(salary) FROM employees;
SELECT GROUP_CONCAT(firstname order by customerid) FROM customer;
```

### Numeric functions (equivalent)

| Oracle | MySQL | Equivalent |
|---|---|---|
| `ABS(-11.3)=11.3` | `ABS` | Yes |
| `CEIL(-24.9)=-24` | `CEIL` | Yes |
| `FLOOR(-43.7)=-44` | `FLOOR` | Yes |
| `MOD(10,3)=1` | `MOD` | Yes |
| `ROUND(3.49,1)=3.5` | `ROUND` | Yes |
| `TRUNC(13.5)=13` | `TRUNCATE(13.5, 0)` — the second argument is mandatory (verified: `TRUNCATE(13.5)` is a syntax error) | Yes (renamed) |

### Character functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `CONCAT('a',1)→a1` | `CONCAT` | Yes |
| `LOWER`/`UPPER` | `LOWER`/`UPPER` | Yes |
| `LPAD('Log-1',10,'**-**')` | `LPAD('Log-1',10,'-')` | Yes |
| `REGEXP_REPLACE('John','[hn].','1')→Jo1` | `REGEXP_REPLACE` (verified: `Jo1`; back-references `$1`) | Yes (MySQL 8) |
| `REGEXP_SUBSTR(...)` | `REGEXP_SUBSTR` | Yes (MySQL 8) |
| `REPLACE('abcdef','abc','123')→123def` | `REPLACE` | Yes |
| `LTRIM`/`RTRIM` (strip char set) | `LTRIM`/`RTRIM` strip spaces only; `TRIM(LEADING 'xy' FROM s)` strips the **whole string** `'xy'` repeatedly, not the character set (verified: `'yxJohn'` is unchanged by `TRIM(LEADING 'x' …)`) — use `REGEXP_REPLACE(s, '^[xy]+', '')` | Partly |
| `SUBSTR('John Smith',6,1)→S` | `SUBSTR`; negative positions count from the end as in Oracle, but **position 0 returns `''`** where Oracle treats 0 as 1 (verified) | Partly |
| `TRIM(both 'x' FROM 'xJohnxx')→John` | `TRIM` | Yes |
| `ASCII('a')→97` | `ASCII` | Yes |
| `INSTR(s, sub)` | `INSTR(s, sub)`; `INSTR(s, sub, pos)` → `LOCATE(sub, s, pos)` (arguments reversed); no occurrence argument — use `REGEXP_INSTR(s, sub, pos, occ)` with an escaped pattern | Partly |
| `LENGTH('John S.')→7` | `CHAR_LENGTH` — MySQL `LENGTH` counts **bytes** (verified: `LENGTH('é')` = 2 in utf8mb4) | No (renamed) |
| `REGEXP_COUNT` | not available (verified); see `regular-expressions.md` | No |
| `REGEXP_INSTR` | `REGEXP_INSTR` | Yes (MySQL 8) |

### Date and time functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `ADD_MONTHS(d,1)` | `DATE_ADD(d, INTERVAL 1 MONTH)`; at month end Oracle keeps the last day (`ADD_MONTHS('29-FEB-24',1)` = 31-MAR) while MySQL gives `2024-03-29` (verified) — wrap with `LAST_DAY()` when `d = LAST_DAY(d)` | Partly |
| `CURRENT_DATE` (date+time) | `CURRENT_DATE` (date only); use `now()`/`current_timestamp` | Partly |
| `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP` | Yes |
| `EXTRACT(YEAR FROM DATE '2017-03-07')→2017` | `EXTRACT` | Yes |
| `LAST_DAY('05-07-2018')→05-31-2018` | `LAST_DAY` | Yes |
| `MONTHS_BETWEEN(sysdate,sysdate-100)→3.25` | `TIMESTAMPDIFF(MONTH, d1, d2)` returns whole months only and differs at month ends (verified: 2023-11-30 → 2024-02-29 gives 2; Oracle gives 3); `PERIOD_DIFF(202402, 202311)` = 3 works on `YYYYMM` | Partly |
| `SYSDATE` | `SYSDATE()` | Yes |
| `SYSTIMESTAMP` | `CURRENT_TIMESTAMP` | Yes |
| `LOCALTIMESTAMP` | `LOCALTIMESTAMP` | Yes |
| `TO_CHAR(sysdate,'DD-MON-YYYY HH24:MI:SS')` | `DATE_FORMAT(SYSDATE(),'%Y-%m-%d %H:%i:%s')` | Yes |
| `TRUNC(d)` / `TRUNC(d,'MM')` / `TRUNC(d,'YYYY')` | `DATE(d)` / `DATE_FORMAT(d,'%Y-%m-01')` / `MAKEDATE(YEAR(d),1)` (verified) | No |

### Encoding/decoding functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `DECODE` (IF-THEN-ELSE) | `CASE` | No |
| `DUMP` | N/A | No |
| `ORA_HASH` | `CRC32`, `MD5`, `SHA2(x,256)` — different values; only use where the hash is not persisted or compared with Oracle | No |

### Null functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `CASE WHEN ... THEN ... END` | `CASE` | Yes |
| `COALESCE(null,'a','b')→a` | `COALESCE` | Yes |
| `NULLIF('a','b')→a` | `NULLIF` | Yes |
| `NVL(null,'a')→a` | `IFNULL` | No (renamed) |
| `NVL2(x,a,b)` | `IF(x IS NOT NULL, a, b)` or `CASE` | No |
| `DECODE(x, NULL, 'm', …)` | `CASE WHEN x IS NULL THEN 'm' …` — `DECODE` treats NULL = NULL, simple `CASE x WHEN NULL` does not match (verified) | No |

### Environment/identifier functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `SYS_GUID()` | `REPLACE(UUID(),'-','')` (32 hex chars), or `UUID_TO_BIN(UUID(), 1)` into `BINARY(16)` for an index-friendly, time-ordered key (verified) | No |
| `UID` | N/A | No |
| `USER` | `USER()` (returns user@machine) | No |
| `USERENV('LANGUAGE')` | `SHOW SESSION VARIABLES LIKE 'collation_connection'` | No |

### Conversion functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `CAST('10' as int)+1→11` | `CAST('10' AS SIGNED)+1` (`INT` is not a `CAST` target type) | Yes |
| `CONVERT('...','US7ASCII','WE8ISO8859P1')` | `CONVERT('...' USING utf8mb4)` (`utf8` is the deprecated alias of `utf8mb3`) | Yes |
| `TO_CHAR('01234')→01234` | `FORMAT('01234',0)→01234` | No |
| `TO_DATE('01Jan2017','DDMonYYYY')` | `STR_TO_DATE('01Jan2017','%d%b%Y')` (`%b` = abbreviated month; verified) | No |
| `TO_NUMBER('01234')→1234` | `CAST('01234' AS DECIMAL(p,s))` (verified); a non-numeric string casts to a prefix or 0 with a warning instead of an error | Partly |

### Aggregate functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `AVG`, `COUNT`, `MAX`, `MIN`, `SUM` | same | Yes |
| `LISTAGG([DISTINCT] firstname,',') within group (order by customerid)` | `GROUP_CONCAT([DISTINCT] firstname ORDER BY customerid SEPARATOR ',')` (verified). Default separator is `,`; output is **silently truncated** at `group_concat_max_len` (1024 bytes by default) | No |

### Top-N query (Oracle 12c)

| Oracle | MySQL | Equivalent |
|---|---|---|
| `SELECT * FROM customer fetch first 10 rows only` | `SELECT * FROM customer LIMIT 10` — `FETCH FIRST` is a syntax error in MySQL (verified); `OFFSET n ROWS FETCH NEXT m ROWS ONLY` → `LIMIT m OFFSET n`; `WITH TIES` → `RANK() OVER` in a derived table | No |

## Conversion notes
- Most numeric/character/aggregate functions map directly; watch renames: `TRUNC→TRUNCATE`, `NVL→IFNULL`, `LISTAGG→GROUP_CONCAT`.
- MySQL `LTRIM`/`RTRIM` only strip spaces (not arbitrary char sets); combine with `REPLACE` for Oracle parity.
- Regex functions `REGEXP_REPLACE`, `REGEXP_SUBSTR`, `REGEXP_INSTR`, `REGEXP_LIKE` exist on Aurora MySQL 3 / 8.4; only `REGEXP_COUNT` must be simulated (see `regular-expressions.md`).
- `ROUND` on exact `DECIMAL` values rounds half away from zero (like Oracle `NUMBER`); on approximate `DOUBLE` values it rounds half to even (verified: `ROUND(2.5e0)` = 2). Keep money columns `DECIMAL`.
- `CURRENT_DATE` in MySQL has no time part; Oracle `CURRENT_DATE`/`SYSDATE` do. Convert `SYSDATE` to `NOW()` (statement start) or `SYSDATE()` (call time) depending on intent.
- `DECODE`→`CASE`, `NVL2`→`CASE`, `SYS_GUID()`→`REPLACE(UUID(),'-','')`, `ORA_HASH`→`SHA`.
- Date arithmetic differs: `ADD_MONTHS`→`DATE_ADD … INTERVAL n MONTH` (month-end differs), `MONTHS_BETWEEN`→`TIMESTAMPDIFF(MONTH, …)` (integer only) or a custom function, `TRUNC(date)`→`DATE()`. `date + 1` (Oracle day arithmetic) → `DATE_ADD(d, INTERVAL 1 DAY)`; in MySQL `d + 1` turns the date into a number (verified: `CURRENT_DATE() + 0` = `20261029`).
