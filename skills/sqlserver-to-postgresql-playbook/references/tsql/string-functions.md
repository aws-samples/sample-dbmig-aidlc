# String Functions

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.stringfunctions.html

**Conversion category:** Automatic (four-star feature compatibility, four-star automation)
**SCT automation:** Four-star automation level; N/A action code

## SQL Server

String functions are scalar functions operating on string input, returning string or numeric values.

| Function | Purpose | Example | Result |
|---|---|---|---|
| `ASCII`, `UNICODE` | char → ASCII/UNICODE code | `SELECT ASCII('A')` | `65` |
| `CHAR`, `NCHAR` | code → char | `SELECT CHAR(65)` | `'A'` |
| `CHARINDEX`, `PATINDEX` | starting position of string/pattern | `SELECT CHARINDEX('ab','xabcdy')` | `2` |
| `CONCAT`, `CONCAT_WS` | combine strings, with/without separator | `SELECT CONCAT('a','b'), CONCAT_WS(',','a','b')` | `'ab', 'a,b'` |
| `LEFT`, `RIGHT`, `SUBSTRING` | partial string by position/length | `SELECT LEFT('abs',2), SUBSTRING('abcd',2,2)` | `'ab', 'bc'` |
| `LOWER`, `UPPER` | case conversion | `SELECT LOWER('ABcd')` | `'abcd'` |
| `LTRIM`, `RTRIM`, `TRIM` | remove leading/trailing spaces | `SELECT LTRIM('abc d ')` | `'abc d '` |
| `STR` | numeric → string | `SELECT STR(3.1415927,5,3)` | `3.142` |
| `REVERSE` | reverse string | `SELECT REVERSE('abcd')` | `'dcba'` |
| `REPLICATE` | concatenated copies | `SELECT REPLICATE('abc', 3)` | `'abcabcabc'` |
| `REPLACE` | replace all occurrences | `SELECT REPLACE('abcd', 'bc', 'xy')` | `'axyd'` |
| `STRING_SPLIT` | parse list (table-valued) | `SELECT * FROM STRING_SPLIT('1,2',',')` | rows `1`,`2` |
| `STRING_AGG` | concatenate values in row groups | `SELECT STRING_AGG(C, ',') ... GROUP BY ID` | `'ab'`, `'c'` |

## PostgreSQL

Most SQL Server string functions are supported. Exceptions:
- `UNICODE` — no direct equivalent; for UTF8 input use `ASCII` for the same result.
- `PATINDEX` — no built-in; create a custom function (see below) for full compatibility.

PostgreSQL also has functions not in SQL Server (e.g., POSIX regular expressions).

| PostgreSQL function | Definition / example |
|---|---|
| `CONCAT` | `concat('a', 1)` → `a1`; also `||`: `select 'a' \|\|' '\|\| 'b'` → `a b` |
| `LOWER` / `UPPER` | `lower('MR. Smith')` → `mr. smith` |
| `LPAD` / `RPAD` | `LPAD('Log-1',10,'@')` → `@@@@@Log-1` |
| `REGEXP_REPLACE` | `regexp_replace('John', '[hn].', '1')` → `Jo1` |
| `REGEXP_MATCHES` / `SUBSTRING` | `REGEXP_MATCHES('http://www.aws.com/products', '(http://[[:alnum:]]+.*/)')` → `{http://www.aws.com/}`; `SUBSTRING(...)` → `http://www.aws.com/` |
| `REPLACE` | `replace('abcdef', 'abc', '123')` → `123def` |
| `LTRIM` / `RTRIM` | `ltrim('zzzyaws', 'xyz')` → `aws` |
| `SUBSTRING` | `substring('John Smith', 6, 1)` → `S` |
| `TRIM` | `trim(both from 'yxJohnxx', 'xyz')` → `John` |
| `ASCII` | `ascii('a')` → `97` |
| `LENGTH` | `length('John S.')` → `7` |

Creating a `PATINDEX` equivalent (0 = not found; first position = 1):

```sql
CREATE OR REPLACE FUNCTION "patindex"( "pattern" VARCHAR, "expression" VARCHAR )
RETURNS INT AS $BODY$
SELECT COALESCE(STRPOS($2,(
  SELECT(REGEXP_MATCHES($2,'(' ||
  REPLACE( REPLACE(TRIM( $1, '%' ), '%', '.*?' ), '_', '.' )
    || ')','i') )[ 1 ] LIMIT 1)),0);
$BODY$ LANGUAGE 'sql' IMMUTABLE;

SELECT patindex( 'Lo%', 'Long String' );    -- 1
SELECT patindex( '%rin%', 'Long String' );  -- 8
SELECT patindex( '%g_S%', 'Long String' );  -- 4
```

## Summary

| SQL Server function | Aurora PostgreSQL function |
|---|---|
| `ASCII` | `ASCII` |
| `UNICODE` | For UTF8 inputs, use `ASCII` |
| `CHAR`, `NCHAR` | `CHR` |
| `CHARINDEX` | `POSITION` |
| `PATINDEX` | custom function (see example) |
| `CONCAT`, `CONCAT_WS` | `CONCAT`, `CONCAT_WS` |
| `LEFT`, `RIGHT`, `SUBSTRING` | `LEFT`, `RIGHT`, `SUBSTRING` |
| `LOWER`, `UPPER` | `LOWER`, `UPPER` |
| `LTRIM`, `RTRIM`, `TRIM` | `LTRIM`, `RTRIM`, `TRIM` |
| `STR` | `TO_CHAR` |
| `REVERSE` | `REVERSE` |
| `REPLICATE` | `LPAD` |
| `REPLACE` | `REPLACE` |
| `STRING_SPLIT` | `regexp_split_to_array` or `regexp_split_to_table` |
| `STRING_AGG` | `STRING_AGG` |

## Conversion notes
- Most functions map directly; main work is renaming (`CHAR`→`CHR`, `CHARINDEX`→`POSITION`, `STR`→`TO_CHAR`).
- `PATINDEX` needs a user-defined function; the playbook provides a ready-made implementation.
- `UNICODE` collapses to `ASCII` under UTF8.
- `||` operator and `CONCAT` both available for concatenation.
- PostgreSQL adds POSIX regex functions (`REGEXP_REPLACE`, `REGEXP_MATCHES`) with no SQL Server equivalent.
