# Single-row and Aggregate Functions

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.aggregate.html

**Conversion category:** Assisted (★★★★ feature compatibility, ★★★★ automation)
**SCT automation:** N/A — MySQL doesn't support all functions; unsupported functions require manual creation.

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
| `TRUNC(13.5)=13` | `TRUNCATE` | Yes (renamed) |

### Character functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `CONCAT('a',1)→a1` | `CONCAT` | Yes |
| `LOWER`/`UPPER` | `LOWER`/`UPPER` | Yes |
| `LPAD('Log-1',10,'**-**')` | `LPAD('Log-1',10,'-')` | Yes |
| `REGEXP_REPLACE('John','[hn].','1')→Jo1` | simulate with built-ins | No |
| `REGEXP_SUBSTR(...)` | simulate with built-ins | No |
| `REPLACE('abcdef','abc','123')→123def` | `REPLACE` | Yes |
| `LTRIM`/`RTRIM` (strip char set) | `LTRIM`/`RTRIM` (spaces only) — combine with `REPLACE` | Partly |
| `SUBSTR('John Smith',6,1)→S` | `SUBSTR` | Yes |
| `TRIM(both 'x' FROM 'xJohnxx')→John` | `TRIM` | Yes |
| `ASCII('a')→97` | `ASCII` | Yes |
| `INSTR` | `INSTR` | Yes |
| `LENGTH('John S.')→7` | `LENGTH` | Yes |
| `REGEXP_COUNT` | simulate with built-ins | No |
| `REGEXP_INSTR` | simulate with built-ins | No |

### Date and time functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `ADD_MONTHS(sysdate,1)` | `ADDDATE` | No |
| `CURRENT_DATE` (date+time) | `CURRENT_DATE` (date only); use `now()`/`current_timestamp` | Partly |
| `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP` | Yes |
| `EXTRACT(YEAR FROM DATE '2017-03-07')→2017` | `EXTRACT` | Yes |
| `LAST_DAY('05-07-2018')→05-31-2018` | `LAST_DAY` | Yes |
| `MONTHS_BETWEEN(sysdate,sysdate-100)→3.25` | `PERIOD_DIFF(201801,201703)→10` (YYMM/YYYYMM) | Partly |
| `SYSDATE` | `SYSDATE()` | Yes |
| `SYSTIMESTAMP` | `CURRENT_TIMESTAMP` | Yes |
| `LOCALTIMESTAMP` | `LOCALTIMESTAMP` | Yes |
| `TO_CHAR(sysdate,'DD-MON-YYYY HH24:MI:SS')` | `DATE_FORMAT(SYSDATE(),'%Y-%m-%d %H:%i:%s')` | Yes |
| `TRUNC(systimestamp)` (date truncation) | simulate with built-ins | No |

### Encoding/decoding functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `DECODE` (IF-THEN-ELSE) | `CASE` | No |
| `DUMP` | N/A | No |
| `ORA_HASH` | `SHA` (SHA-1 160-bit) | No |

### Null functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `CASE WHEN ... THEN ... END` | `CASE` | Yes |
| `COALESCE(null,'a','b')→a` | `COALESCE` | Yes |
| `NULLIF('a','b')→a` | `NULLIF` | Yes |
| `NVL(null,'a')→a` | `IFNULL` | No (renamed) |
| `NVL2` | `CASE` | No |

### Environment/identifier functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `SYS_GUID()` | `REPLACE(UUID(),'-','')` | No |
| `UID` | N/A | No |
| `USER` | `USER()` (returns user@machine) | No |
| `USERENV('LANGUAGE')` | `SHOW SESSION VARIABLES LIKE 'collation_connection'` | No |

### Conversion functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `CAST('10' as int)+1→11` | `CAST('10' as UNSIGNED)+1` | Yes |
| `CONVERT('...','US7ASCII','WE8ISO8859P1')` | `CONVERT('...' USING utf8)` | Yes |
| `TO_CHAR('01234')→01234` | `FORMAT('01234',0)→01234` | No |
| `TO_DATE('01Jan2017','DDMonYYYY')` | `STR_TO_DATE('01Jan2017','%d%M%Y')` | No |
| `TO_NUMBER('01234')→1234` | N/A | No |

### Aggregate functions

| Oracle | MySQL | Equivalent |
|---|---|---|
| `AVG`, `COUNT`, `MAX`, `MIN`, `SUM` | same | Yes |
| `LISTAGG(firstname,',') within group (order by customerid)` | `GROUP_CONCAT(firstname order by customerid)` | No |

### Top-N query (Oracle 12c)

| Oracle | MySQL | Equivalent |
|---|---|---|
| `SELECT * FROM customer fetch first 10 rows only` | `SELECT * FROM customer LIMIT 10` | Yes |

## Conversion notes
- Most numeric/character/aggregate functions map directly; watch renames: `TRUNC→TRUNCATE`, `NVL→IFNULL`, `LISTAGG→GROUP_CONCAT`.
- MySQL `LTRIM`/`RTRIM` only strip spaces (not arbitrary char sets); combine with `REPLACE` for Oracle parity.
- Regex functions (`REGEXP_REPLACE`, `REGEXP_SUBSTR`, `REGEXP_COUNT`, `REGEXP_INSTR`) have no direct MySQL equivalent — simulate with MySQL built-in regex functions.
- `DECODE`→`CASE`, `NVL2`→`CASE`, `SYS_GUID()`→`REPLACE(UUID(),'-','')`, `ORA_HASH`→`SHA`.
- Date arithmetic differs: `ADD_MONTHS`→`ADDDATE`, `MONTHS_BETWEEN`→`PERIOD_DIFF` (period format YYMM/YYYYMM), `TRUNC(date)` must be simulated.
