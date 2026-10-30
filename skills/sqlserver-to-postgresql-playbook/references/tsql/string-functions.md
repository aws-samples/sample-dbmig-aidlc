# String Functions

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.stringfunctions.html

**Conversion category:** Automatic (four-star feature compatibility, four-star automation)
**SCT automation:** Four-star automation level; N/A action code

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Replaced the PATINDEX function with a verified anchored, metacharacter-safe version (original returned wrong positions); fixed REPLICATE→repeat (was LPAD); added LEN trailing-space, DATALENGTH, STRING_SPLIT→string_to_table WITH ORDINALITY, CHARINDEX start, STUFF, QUOTENAME and fuzzystrmatch mappings (all verified).

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

Creating a `PATINDEX` equivalent (0 = not found; first position = 1). Verified on Aurora PostgreSQL 18.6; uses PG 15 `regexp_instr`:

```sql
-- Translates the LIKE pattern to a regex: % → .*, _ → ., [..]/[^..] kept, other regex
-- metacharacters escaped; a pattern without a leading/trailing % is anchored, as in SQL Server.
-- 'i' = case-insensitive, matching the usual *_CI_* collation; drop it for a CS collation.
CREATE OR REPLACE FUNCTION patindex(pattern text, expression text)
RETURNS integer LANGUAGE sql IMMUTABLE PARALLEL SAFE
RETURN regexp_instr(expression,
         CASE WHEN left(pattern, 1) = '%' THEN '' ELSE '^' END
         || replace(replace(
              regexp_replace(regexp_replace(trim(both '%' from pattern),
                '([.$+?(){}|*\\])', '\\\1', 'g'),
                '(?<!\[)\^', '\\^', 'g'),
              '%', '.*'), '_', '.')
         || CASE WHEN right(pattern, 1) = '%' THEN '' ELSE '$' END,
         1, 1, 0, 'i');

SELECT patindex('Lo%',     'Long String');  -- 1
SELECT patindex('%rin%',   'Long String');  -- 8
SELECT patindex('%g_S%',   'Long String');  -- 4
SELECT patindex('Lo%',     'xLong');        -- 0  (anchored)
SELECT patindex('%ng',     'Long String');  -- 10 (anchored at end)
SELECT patindex('%[^a-z]%','abc1');         -- 4
SELECT patindex('%a.b%',   'axb');          -- 0  ('.' is literal in LIKE)
```

> Correction: the original playbook function ignored anchoring (`patindex('Lo%','xLong')` returned 2 and `patindex('%ng','Long String')` returned 3; SQL Server returns 0 and 10) and treated `.`, `(`, `+` as regex metacharacters. Verified on 18.6. Escape-character patterns (`ESCAPE` / `[%]`) still need review.

## PostgreSQL 18 notes (verified on Aurora PostgreSQL 18.6)

- **`LEN` vs `length`.** SQL Server `LEN` ignores trailing spaces; PostgreSQL `length('ab  '::varchar)` = 4. Convert `LEN(x)` → `length(rtrim(x))` unless the column is `char(n)` (where `length` already ignores padding). `DATALENGTH` → `octet_length` (UTF-8: `'é'` = 2 bytes; SQL Server `nvarchar` would give 2 per character, `varchar` with a Latin collation 1).
- **`REPLICATE(s, n)` → `repeat(s, n)`.** The original table mapped it to `LPAD`, which truncates or pads to a total length and is wrong for this purpose.
- **`STRING_SPLIT(s, ',')` → `string_to_table(s, ',')`** (PG 14). `STRING_SPLIT(s, ',', 1)` (with `ordinal`, SQL Server 2022) → `string_to_table(s, ',') WITH ORDINALITY AS t(value, ordinal)`. Empty items are returned as `''` in both. SQL Server does not guarantee order without `enable_ordinal`; do not add an `ORDER BY` assumption.
- `CHARINDEX(sub, s)` → `strpos(s, sub)` (argument order reversed) or `position(sub IN s)`; `CHARINDEX(sub, s, start)` → `CASE WHEN strpos(substr(s, start), sub) = 0 THEN 0 ELSE strpos(substr(s, start), sub) + start - 1 END`. Matching is case-sensitive in PostgreSQL unless the column has a nondeterministic collation (see `collations.md`).
- `STUFF(s, start, len, new)` → `overlay(s PLACING new FROM start FOR len)`. `TRANSLATE` exists in both.
- `QUOTENAME(x)` → `quote_ident(x)` or `format('%I', x)` (double quotes, not brackets). `FORMATMESSAGE`/`FORMAT` string templates → `format()` with `%s`/`%I`/`%L`.
- `STR(n, len, dec)` → `to_char(n, 'FM…')` with a picture string; `STR` right-justifies to `len`, so add `lpad` if the width matters.
- `UNICODE(c)` → `ascii(c)` (returns the code point under UTF-8, verified: `ascii('é')` = 233); `NCHAR(n)` → `chr(n)`.
- `SOUNDEX`/`DIFFERENCE` → `fuzzystrmatch` extension (`soundex`, `difference`, verified).
- `+` concatenation: `'a' + NULL` and `'a' || NULL` both give NULL (with `CONCAT_NULL_YIELDS_NULL ON`); `CONCAT` and `CONCAT_WS` skip NULLs in both.
- PG 15 added `regexp_count`, `regexp_instr`, `regexp_like`, `regexp_substr`. PG 18 added `casefold()` for case-insensitive comparisons.

## Summary

| SQL Server function | Aurora PostgreSQL function |
|---|---|
| `ASCII` | `ASCII` |
| `UNICODE` | For UTF8 inputs, use `ASCII` |
| `CHAR`, `NCHAR` | `CHR` |
| `CHARINDEX` | `STRPOS` / `POSITION` (argument order differs) |
| `PATINDEX` | custom function (see example) |
| `LEN` | `LENGTH(RTRIM(x))` |
| `DATALENGTH` | `OCTET_LENGTH` |
| `STUFF` | `OVERLAY` |
| `QUOTENAME` | `QUOTE_IDENT` / `FORMAT('%I')` |
| `CONCAT`, `CONCAT_WS` | `CONCAT`, `CONCAT_WS` |
| `LEFT`, `RIGHT`, `SUBSTRING` | `LEFT`, `RIGHT`, `SUBSTRING` |
| `LOWER`, `UPPER` | `LOWER`, `UPPER` |
| `LTRIM`, `RTRIM`, `TRIM` | `LTRIM`, `RTRIM`, `TRIM` |
| `STR` | `TO_CHAR` |
| `REVERSE` | `REVERSE` |
| `REPLICATE` | `REPEAT` |
| `REPLACE` | `REPLACE` |
| `STRING_SPLIT` | `string_to_table` (PG 14; `WITH ORDINALITY` for the ordinal) |
| `STRING_AGG` | `STRING_AGG` |

## Conversion notes
- Most functions map directly; main work is renaming (`CHAR`→`CHR`, `CHARINDEX`→`POSITION`, `STR`→`TO_CHAR`).
- `PATINDEX` needs a user-defined function; the playbook provides a ready-made implementation.
- `UNICODE` collapses to `ASCII` under UTF8.
- `||` operator and `CONCAT` both available for concatenation.
- PostgreSQL adds POSIX regex functions (`REGEXP_REPLACE`, `REGEXP_MATCHES`, and PG 15 `REGEXP_COUNT/INSTR/LIKE/SUBSTR`); SQL Server 2025 adds `REGEXP_*` functions with similar names but its own regex dialect, so test each pattern.
- `REPLICATE` → `repeat` (not `LPAD`); `LEN` → `length(rtrim())`; `STRING_SPLIT` → `string_to_table`.
