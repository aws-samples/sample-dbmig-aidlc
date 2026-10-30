# String functions for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.stringfunctions.html

**Conversion category:** Automatic (Four star feature compatibility)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected STRING_SPLIT and STRING_AGG (JSON_TABLE and GROUP_CONCAT on MySQL 8 — verified) and STR (FORMAT adds separators); added LEN, DATALENGTH, STUFF, QUOTENAME, PATINDEX→REGEXP_INSTR, CHARINDEX start, '+' concatenation — all verified.

## SQL Server

String functions are typically scalar functions operating on string input, returning a string or numeric value.

| Function | Purpose | Example | Result |
|---|---|---|---|
| `ASCII`, `UNICODE` | Char → ASCII/UNICODE code | `SELECT ASCII('A')` | 65 |
| `CHAR`, `NCHAR` | Code → string character | `SELECT CHAR(65)` | 'A' |
| `CHARINDEX`, `PATINDEX` | Find start position of substring/pattern | `SELECT CHARINDEX('ab', 'xabcdy')` | 2 |
| `CONCAT`, `CONCAT_WS` | Combine strings, with/without separator | `SELECT CONCAT('a','b'), CONCAT_WS(',','a','b')` | 'ab', 'a,b' |
| `LEFT`, `RIGHT`, `SUBSTRING` | Partial string by position/length | `SELECT LEFT('abs',2), SUBSTRING('abcd',2,2)` | 'ab', 'bc' |
| `LOWER`, `UPPER` | Change letter case | `SELECT LOWER('ABcd')` | 'abcd' |
| `LTRIM`, `RTRIM`, `TRIM` | Remove leading/trailing spaces | `SELECT LTRIM('abc d ')` | 'abc d ' |
| `STR` | Numeric → string | `SELECT STR(3.1415927,5,3)` | 3.142 |
| `REVERSE` | Reverse string | `SELECT REVERSE('abcd')` | 'dcba' |
| `REPLICATE` | Concatenated copies of a string | `SELECT REPLICATE('abc', 3)` | 'abcabcabc' |
| `REPLACE` | Replace all occurrences | `SELECT REPLACE('abcd', 'bc', 'xy')` | 'axyd' |
| `STRING_SPLIT` | Table-valued: split delimited list to rows | `SELECT * FROM STRING_SPLIT('1,2',',')` | 1 / 2 |
| `STRING_AGG` | Aggregate: concatenate row values | `SELECT STRING_AGG(C, ',') FROM ... GROUP BY ID` | 'ab' / 'c' |

## MySQL

Aurora MySQL supports a larger set of string functions than SQL Server, including regular expressions (`REGEXP`, `RLIKE`) that SQL Server lacks.

| Function | Purpose | Example | Result |
|---|---|---|---|
| `ASCII`, `ORD` | Char → ASCII/multi-byte code | `SELECT ASCII('A')` | 65 |
| `CHAR` | Code → character | `SELECT CHAR(65)` | 'A' |
| `LOCATE` | Find start position of substring | `SELECT LOCATE('ab', 'xabcdy')` | 2 |
| `CONCAT`, `CONCAT_WS` | Combine strings, with/without separator | `SELECT CONCAT('a','b'), CONCAT_WS(',','a','b')` | 'ab', 'a,b' |
| `LEFT`, `RIGHT`, `SUBSTRING` | Partial string | `SELECT LEFT('abs',2), SUBSTRING('abcd',2,2)` | 'ab', 'bc' |
| `LOWER`, `UPPER` | Change letter case (no effect on binary collations) | `SELECT LOWER('ABcd')` | 'abcd' |
| `LTRIM`, `RTRIM`, `TRIM` | Remove leading/trailing chars (not just spaces) | `SELECT TRIM(LEADING 'x' FROM 'xxxabcxxx')` | 'abcxxx' |
| `FORMAT` | Numeric → string | `SELECT FORMAT(3.1415927,5)` | 3.14159 |
| `REVERSE` | Reverse string | `SELECT REVERSE('abcd')` | 'dcba' |
| `REPEAT` | Concatenated copies | `SELECT REPEAT('abc', 3)` | 'abcabcabc' |
| `REPLACE` | Replace all occurrences | `SELECT REPLACE('abcd', 'bc','xy')` | 'axyd' |

`TRIM` syntax: `TRIM ([{BOTH | LEADING | TRAILING} [<Remove String>] FROM] <String>)`.

## Conversion notes

- Aurora MySQL does not handle ASCII and UNICODE separately — any string is UNICODE or ASCII depending on its collation property (see Collations / Data Types).
- `LOWER`/`UPPER` have no effect on binary collation strings; convert to a non-binary collation first.
- Use `FIND_IN_SET`, `SUBSTRING_INDEX` for delimited-list element handling.
- Aurora MySQL adds `REGEXP`/`RLIKE`, `MID`, `SUBSTR` (synonyms of `SUBSTRING`) and, on 3 / 8.4, `REGEXP_LIKE`, `REGEXP_INSTR`, `REGEXP_SUBSTR`, `REGEXP_REPLACE` (no `REGEXP_COUNT`; back-references are `$1`).
- Comparisons and `LIKE` follow the collation: the default `utf8mb4_0900_ai_ci` is case- **and accent**-insensitive and treats trailing spaces as significant (see `collations.md`).

| SQL Server function | Aurora MySQL function | Comments |
|---|---|---|
| `ASCII`, `UNICODE` | `ASCII`, `ORD` | Compatible |
| `CHAR`, `NCHAR` | `CHAR` | Aurora `CHAR` accepts a list of values and concatenates |
| `CHARINDEX(sub, s [, start])` | `LOCATE(sub, s [, start])` | same argument order; start works (verified) |
| `PATINDEX('%pat%', s)` | `REGEXP_INSTR(s, 'regex')` | MySQL 8: translate the LIKE pattern (`%`→`.*`, `_`→`.`, keep `[…]`) (verified `REGEXP_INSTR('Long String','g.S')` = 4) |
| `CONCAT`, `CONCAT_WS` | `CONCAT`, `CONCAT_WS` | Compatible |
| `LEFT`, `RIGHT`, `SUBSTRING` | `LEFT`, `RIGHT`, `SUBSTRING` (+`MID`,`SUBSTR`) | Compatible. `SUBSTRING_INDEX` for delimited lists |
| `LOWER`, `UPPER` | `LOWER`, `UPPER` | Compatible; no effect on binary collations |
| `LTRIM`, `RTRIM`, `TRIM` | `LTRIM`, `RTRIM`, `TRIM` | Aurora `TRIM` not limited to spaces/both ends |
| `STR(n, len, dec)` | `LPAD(CAST(ROUND(n, dec) AS CHAR), len, ' ')` | *(corrected)* `FORMAT` adds thousands separators (`1,234.57`, verified) — use it only for display formatting |
| `LEN(s)` | `CHAR_LENGTH(RTRIM(s))` | `LEN` ignores trailing spaces; `CHAR_LENGTH('ab  ')` = 4 (verified) |
| `DATALENGTH(s)` | `LENGTH(s)` | bytes (`LENGTH('é')` = 2 in utf8mb4, verified) — never use MySQL `LENGTH` for character counts |
| `STUFF(s, start, len, new)` | `INSERT(s, start, len, new)` | verified (`aXYef`) |
| `QUOTENAME(x)` | ``CONCAT('`', REPLACE(x, '`', '``'), '`')`` | backticks, doubled inside (verified) |
| `+` string concatenation | `CONCAT()` | `'a' + 'b'` is numeric addition = 0 in MySQL (verified) |
| `REVERSE` | `REVERSE` | Compatible |
| `REPLICATE` | `REPEAT` | Compatible arguments |
| `REPLACE` | `REPLACE` | Compatible |
| `STRING_SPLIT(s, ',')` | `JSON_TABLE(CONCAT('["', REPLACE(s, ',', '","'), '"]'), '$[*]' COLUMNS (ordinal FOR ORDINALITY, value VARCHAR(100) PATH '$'))` | *(corrected)* set-based on MySQL 8 (verified, including empty items); escape `"` and `\` in the input first |
| `STRING_AGG(x, sep) WITHIN GROUP (ORDER BY y)` | `GROUP_CONCAT(x ORDER BY y SEPARATOR sep)` | *(corrected)* supported (verified); truncated at `group_concat_max_len` (1024 bytes default) |
| `TRANSLATE(s, from, to)` | nested `REPLACE` | no `TRANSLATE` |
| `FORMAT(value, fmt, culture)` | `FORMAT(n, dec, locale)` / `DATE_FORMAT` | different format model |
