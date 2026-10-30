# CAST and CONVERT

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.castconvert.html

**Conversion category:** Assisted (three-star feature compatibility)
**SCT automation:** Four-star automation level; N/A action code

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): `CONVERT` style table and fixed style-109 example (verified), PG 16 `pg_input_is_valid` as the `TRY_CAST` equivalent (verified), `FORMAT`/`PARSE` mapping, implicit-conversion note.

## SQL Server

`CAST` and `CONVERT` convert one data type to another and behave mostly the same. Differences:
- `CAST` is part of ANSI-SQL; `CONVERT` is not.
- `CONVERT` accepts an optional `style` parameter for formatting (especially dates).

Syntax:

```sql
-- CAST Syntax:
CAST ( expression AS data_type [ ( length ) ] )

-- CONVERT Syntax:
CONVERT ( data_type [ ( length ) ] , expression [ , style ] )
```

Examples:

```sql
SELECT CAST('23' AS int) AS [int], CAST(23 AS decimal(10, 2)) AS [decimal];

SELECT CONVERT(int, '23') AS [int], CONVERT(decimal(10, 2), 23) AS [decimal];
-- int  decimal
-- 23   23.00

-- Convert a date with style 109 (mon dd yyyy hh:mi:ss:mmmAM (or PM)):
SELECT CONVERT(nvarchar(30), GETDATE(), 109);
-- Jul 25 2018 5:20:10.8975085PM
```

## PostgreSQL

Aurora PostgreSQL provides the same `CAST` function for type conversion. It also has a `CONVERSION` function, but it is **not** equivalent to SQL Server `CONVERT` — PostgreSQL `CONVERSION`/`CREATE CONVERSION` converts between character set encodings (e.g., UTF8 and LATIN). If `CONVERT` is used in SQL Server code, rewrite it to use `CAST`.

`CREATE CAST` defines a new cast between two data types; casts can be EXPLICIT or IMPLICIT. You can create custom casts (e.g., with `WITHOUT FUNCTION`) to change default behavior. PostgreSQL also supports the `::` operator for casts, which keeps PL/pgSQL cleaner.

Syntax:

```sql
CREATE CAST (source_type AS target_type)
WITH FUNCTION function_name (argument_type [, ...]) [ AS ASSIGNMENT | AS IMPLICIT ]

CREATE CAST (source_type AS target_type)
WITHOUT FUNCTION [ AS ASSIGNMENT | AS IMPLICIT ]

CREATE CAST (source_type AS target_type)
WITH INOUT [ AS ASSIGNMENT | AS IMPLICIT ]
```

Examples:

```sql
SELECT 23 + 2.0;
-- or
SELECT CAST ( 23 AS numeric ) + 2.0;

-- Date format equivalent of CONVERT style 109 (verified on 18.6):
SELECT TO_CHAR(timestamp '2024-07-25 17:20:10.897', 'Mon DD YYYY HH12:MI:SS:MSAM');
-- Jul 25 2024 05:20:10:897PM

-- Using :: operator:
SELECT '2.35'::DECIMAL + 4.5 AS results;
-- results
-- 6.85
```

## Summary

| Option | SQL Server | Aurora PostgreSQL |
|---|---|---|
| Explicit `CAST` | `SELECT CAST('23.7' AS varchar) AS int` | `SELECT CAST('23.7' AS varchar) AS int` |
| Explicit `CONVERT` | `SELECT CONVERT (VARCHAR, '23.7')` | Need to use `CAST` |
| Implicit casting | `SELECT 23 + 2.0` | `SELECT 23 + 2.0` |
| Convert to date format `'mon dd yyyy hh:mi:ss:mmmAM'` | `SELECT CONVERT(nvarchar(30), GETDATE(), 109)` | `SELECT TO_CHAR(NOW(),'Mon DD YYYY HH:MI:SS:MSAM')` |

## Conversion notes
- `CAST` syntax is essentially identical between the two engines.
- Rewrite `CONVERT` as `CAST`; PostgreSQL `CONVERT`/`CONVERSION` is for encoding only, not data type conversion.
- Date-style `CONVERT(..., style)` calls must be rewritten as `TO_CHAR(...)` with an explicit format mask.
- Not all SQL Server data types exist in PostgreSQL — you may need to change the target data type as well, not just the CAST/CONVERT call.
- `::` operator is a concise PostgreSQL-idiomatic alternative to `CAST`.

### `CONVERT` style codes → `to_char` / `to_timestamp` (verified on 18.6)

| Style | SQL Server output | PostgreSQL |
|---|---|---|
| 101 | `07/25/2024` | `to_char(d, 'MM/DD/YYYY')` |
| 103 | `25/07/2024` | `to_char(d, 'DD/MM/YYYY')` |
| 109 | `Jul 25 2024  5:20:10:897PM` | `to_char(ts, 'Mon DD YYYY HH12:MI:SS:MSAM')` |
| 112 | `20240725` | `to_char(d, 'YYYYMMDD')` |
| 120 / 121 | `2024-07-25 17:20:10[.123]` | `to_char(ts, 'YYYY-MM-DD HH24:MI:SS[.MS]')` |
| 126 (ISO 8601) | `2024-07-25T17:20:10.123` | `to_char(ts, 'YYYY-MM-DD"T"HH24:MI:SS.MS')` |

The reverse direction (`CONVERT(datetime, '25/07/2024', 103)`) → `to_timestamp('25/07/2024', 'DD/MM/YYYY')` (or `to_date` for a date-only result).

### `TRY_CAST` / `TRY_CONVERT` / `TRY_PARSE`

PostgreSQL has no `TRY_CAST`, but **PostgreSQL 16 added `pg_input_is_valid(text, type)`** and `pg_input_error_info(text, type)` (verified on 18.6: `pg_input_is_valid('23x','integer') = false`). A safe conversion that needs no exception block:
```sql
CASE WHEN pg_input_is_valid(s, 'integer') THEN s::integer END        -- ≈ TRY_CAST(s AS int)
CASE WHEN pg_input_is_valid(s, 'date')    THEN s::date END           -- invalid dates such as 2024-02-30 → NULL
```
This avoids a PL/pgSQL `EXCEPTION` block per row, which costs a subtransaction.
- `PARSE(s AS datetime USING 'en-US')` → `to_timestamp(s, '<format>')` (culture-specific parsing has no equivalent).
- `FORMAT(n, 'N2')` / `FORMAT(d, 'yyyy-MM-dd')` → `to_char(n, 'FM999G999D00')` / `to_char(d, 'YYYY-MM-DD')`. PostgreSQL's own `format()` is printf-style string formatting, not .NET formatting.
- Implicit conversions: SQL Server converts strings to numbers and dates implicitly in comparisons and concatenation. PostgreSQL usually refuses (`operator does not exist: integer = text`). Add explicit casts, and treat failures as data-quality findings.
