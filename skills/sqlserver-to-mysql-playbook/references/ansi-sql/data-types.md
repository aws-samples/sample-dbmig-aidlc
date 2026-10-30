# Data Types for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.datatypes.html

**Conversion category:** Assisted (Four star feature compatibility)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected TIME(n) (supported), 0x literals (supported), UCS-2 advice (use utf8mb4), row-size limit (65,535 bytes, verified); aligned with the toolkit map (BIT, DATETIME(3), DATETIMEOFFSET, UNIQUEIDENTIFIER, ROWVERSION, MONEY); NCHAR = utf8mb3 trap, DATETIME2 rounding, TIMESTAMP 2038 — verified.

**Key differences:** Minor syntax and handling differences. No special `UNICODE` data types.

## SQL Server

| Category | Data Types |
|---|---|
| Numeric | `BIT`, `TINYINT`, `SMALLINT`, `INT`, `BIGINT`, `NUMERIC`, `DECIMAL`, `MONEY`, `SMALLMONEY`, `FLOAT`, `REAL` |
| String/character | `CHAR`, `VARCHAR`, `NCHAR`, `NVARCHAR` |
| Temporal | `DATE`, `TIME`, `SMALLDATETIME`, `DATETIME`, `DATETIME2`, `DATETIMEOFFSET` |
| Binary | `BINARY`, `VARBINARY` |
| LOB | `TEXT`, `NTEXT`, `IMAGE`, `VARCHAR(MAX)`, `NVARCHAR(MAX)`, `VARBINARY(MAX)` |
| Cursor | `CURSOR` |
| GUID | `UNIQUEIDENTIFIER` |
| Hierarchical | `HIERARCHYID` |
| Spatial | `GEOMETRY`, `GEOGRAPHY` |
| Sets (table type) | `TABLE` |
| XML | `XML` |
| Other | `ROW VERSION`, `SQL_VARIANT` |

`TEXT`, `NTEXT`, `IMAGE` deprecated since SQL Server 2008 R2 — replaced by `VARCHAR(MAX)`, `NVARCHAR(MAX)`, `VARBINARY(MAX)`. AWS SCT converts `TEXT`/`NTEXT` → `LONGTEXT`, `IMAGE` → `LONGBLOB`.

```sql
CREATE TABLE MyTable
(
    Col1 AS INTEGER NOT NULL PRIMARY KEY,
    Col2 AS NVARCHAR(100) NOT NULL
);
```

## MySQL

| Category | Data Types |
|---|---|
| Numeric | `BIT`, `INTEGER`, `SMALLINT`, `TINYINT`, `MEDIUMINT`, `BIGINT`, `DECIMAL`, `NUMERIC`, `FLOAT`, `DOUBLE` |
| String/character | `CHAR`, `VARCHAR`, `SET` |
| Temporal | `DATE`, `DATETIME`, `TIMESTAMP`, `TIME`, `YEAR` |
| Binary | `BINARY`, `VARBINARY` |
| LOB | `BLOB`, `TEXT` |
| Cursor | `CURSOR` |
| Spatial | `GEOMETRY`, `POINT`, `LINESTRING`, `POLYGON`, `MULTIPOINT`, `MULTILINESTRING`, `MULTIPOLYGON`, `GEOMETRYCOLLECTION` |
| JSON | `JSON` |

Aurora MySQL handles out-of-range/overflow differently — SQL Server always raises an error; Aurora MySQL raises an error only in strict mode. Aurora's default `sql_mode` is **empty** (default parameter groups, verified on 3.13 and 8.4.8 on 2026-10-30), so an application connection stores out-of-range and too-long values clipped or truncated with only a warning. With `STRICT_TRANS_TABLES` set (custom parameter group, or the session mode dbmig uses) out-of-range inserts into InnoDB tables fail (error 1264 for 300 into `TINYINT UNSIGNED`, verified), but `1/0` still returns NULL unless `ERROR_FOR_DIVISION_BY_ZERO` is also set. *(Corrected: this said the Aurora default is `STRICT_TRANS_TABLES`.)* Use **`utf8mb4`** for Unicode (the server default); UCS-2, mentioned by the original, is not needed. The whole row (excluding `TEXT`/`BLOB`) is limited to **65,535 bytes**: two `VARCHAR(10000)` columns in `utf8mb4` already fail with error 1118 (verified), so large `NVARCHAR(n)` columns often must become `TEXT`.

## Conversion notes

Data type mapping table:

| SQL Server | Aurora MySQL | Comments |
|---|---|---|
| `BIT` | `TINYINT(1)` (toolkit map) | `BIT(1)` also works (`b'1'`, verified) but drivers return it as bytes; `TINYINT(1)` (= `BOOLEAN`) is friendlier to ORMs. |
| `TINYINT` | `TINYINT` | SQL Server only unsigned (0–255). Aurora MySQL default signed; specify `TINYINT UNSIGNED` for compatibility. |
| `SMALLINT` | `SMALLINT` | SQL Server signed only. Aurora MySQL also `SMALLINT UNSIGNED` (0–65535). |
| `INTEGER` | `INTEGER` | Aurora MySQL also `INTEGER UNSIGNED` and `MEDIUMINT` (3 bytes). |
| `BIGINT` | `BIGINT` | Aurora MySQL also `BIGINT UNSIGNED` (0 to 2^64-1). |
| `NUMERIC` / `DECIMAL` | `NUMERIC` / `DECIMAL` | Synonymous. |
| `MONEY` / `SMALLMONEY` | `DECIMAL(19,4)` / `DECIMAL(10,4)` | toolkit map; remove monetary sign literals. |
| `FLOAT` / `REAL` | `FLOAT` / `REAL` / `DOUBLE` | Aurora MySQL `DOUBLE PRECISION` always 8 bytes. Supports non-standard `FLOAT(M,D)`. |
| `CHAR` | `CHAR` / `VARCHAR` | Aurora MySQL `CHAR` max 255 chars (SQL Server 8000). Use `VARCHAR` beyond 255. |
| `VARCHAR` | `VARCHAR` | Aurora MySQL up to 65,535 chars (subject to row size limit). |
| `NCHAR` | `CHAR` (utf8mb4) | Do **not** use MySQL `NCHAR`: it means `utf8mb3` and rejects 4-byte characters (error 1366, verified). |
| `NVARCHAR` | `VARCHAR` (utf8mb4) | Same; MySQL `NVARCHAR` is `utf8mb3`. |
| `DATE` | `DATE` | Aurora MySQL range 1000-01-01 to 9999-12-31 (no dates before 1000 AD). |
| `TIME(n)` | `TIME(n)` | *(corrected)* `TIME(0..6)` is supported (verified `TIME(6)`); SQL Server `TIME(7)` → `TIME(6)`. Range -838:59:59 to 838:59:59. |
| `SMALLDATETIME` | `DATETIME` / `TIMESTAMP` | Not supported — use `DATETIME`. |
| `DATETIME` | `DATETIME(3)` | toolkit map; SQL Server `datetime` rounds to ~3.33 ms — validate equivalence at second granularity. |
| `DATETIME2(p)` | `DATETIME(min(p,6))` | 7th fractional digit is **rounded** (`.1234567` → `.123457`, verified). Range 1000-01-01 to 9999-12-31; earlier dates are accepted but unsupported. |
| `DATETIMEOFFSET` | `DATETIME(p)` in UTC (+ an offset column if needed) | toolkit map. `TIMESTAMP` converts via the session `time_zone` and **ends 2038-01-19** (insert of 2038-01-20 fails, verified) — avoid it for business dates. |
| `BINARY` | `BINARY` / `VARBINARY` | Max 255 (use `VARBINARY` beyond). *(corrected)* `0x0A0B` hex literals work (verified). |
| `VARBINARY` | `VARBINARY` | Up to 65,535 bytes, within the row-size limit. `0x…` literals work. |
| `TEXT` / `VARCHAR(MAX)` | `VARCHAR` / `TEXT` / `MEDIUMTEXT` / `LONGTEXT` | Pick by length: 2^16-1 → VARCHAR/TEXT; 2^24-1 → MEDIUMTEXT; 2^32-1 → LONGTEXT. |
| `NTEXT` / `NVARCHAR(MAX)` | `VARCHAR` / `TEXT` / `MEDIUMTEXT` / `LONGTEXT` | No special UNICODE type — use `CHARACTER SET`/`COLLATE`. |
| `IMAGE` / `VARBINARY(MAX)` | `VARBINARY` / `BLOB` / `MEDIUMBLOB` / `LONGBLOB` | Pick by length similarly. |
| `CURSOR` | `CURSOR` | Not really a type in Aurora MySQL. |
| `UNIQUEIDENTIFIER` | `CHAR(36)` (toolkit map) or `BINARY(16)` | `NEWID()` → `UUID()`; `NEWSEQUENTIALID()` → `UUID_TO_BIN(UUID(), 1)` (time-ordered, verified 16 bytes). Byte order differs from SQL Server's GUID sort. |
| `HIERARCHYID` | N/A | Rewrite with adjacency list / nested set / closure table / materialized path. |
| `GEOMETRY` | `GEOMETRY` | Syntax/functionality differs significantly — rewrite required. |
| `TABLE` | N/A | No `TABLE` data type. |
| `XML` | N/A | No native XML — use `JSON` or string BLOBs. |
| `ROWVERSION` / `TIMESTAMP` | `BINARY(8)` (toolkit map) / counter | No auto-maintained version; use a `BEFORE UPDATE` trigger (see `creating-tables.md`). Never map SQL Server `timestamp` to MySQL `TIMESTAMP`. |
| `SQL_VARIANT` | N/A | Rewrite to use explicit types. |
