# Data Types for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.datatypes.html

**Conversion category:** Assisted (Four star feature compatibility)
**SCT automation:** Four star automation level

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

Aurora MySQL handles out-of-range/overflow differently — SQL Server always raises an error; Aurora MySQL may clip the value if `STRICT SQL` mode isn't set. Aurora MySQL supports UCS-2 collation, compatible with SQL Server `UNICODE` types. `VARCHAR`/`VARBINARY` can store up to ~32 KB (vs SQL Server's 8 KB limit), so non-LOB types may be more efficient.

## Conversion notes

Data type mapping table:

| SQL Server | Aurora MySQL | Comments |
|---|---|---|
| `BIT` | `BIT` | Aurora MySQL supports `BIT(m)`. Literals use `b'value'` or `0bvalue`. |
| `TINYINT` | `TINYINT` | SQL Server only unsigned (0–255). Aurora MySQL default signed; specify `TINYINT UNSIGNED` for compatibility. |
| `SMALLINT` | `SMALLINT` | SQL Server signed only. Aurora MySQL also `SMALLINT UNSIGNED` (0–65535). |
| `INTEGER` | `INTEGER` | Aurora MySQL also `INTEGER UNSIGNED` and `MEDIUMINT` (3 bytes). |
| `BIGINT` | `BIGINT` | Aurora MySQL also `BIGINT UNSIGNED` (0 to 2^64-1). |
| `NUMERIC` / `DECIMAL` | `NUMERIC` / `DECIMAL` | Synonymous. |
| `MONEY` / `SMALLMONEY` | N/A | No monetary type — use `NUMERIC`/`DECIMAL`; remove monetary sign literals. |
| `FLOAT` / `REAL` | `FLOAT` / `REAL` / `DOUBLE` | Aurora MySQL `DOUBLE PRECISION` always 8 bytes. Supports non-standard `FLOAT(M,D)`. |
| `CHAR` | `CHAR` / `VARCHAR` | Aurora MySQL `CHAR` max 255 chars (SQL Server 8000). Use `VARCHAR` beyond 255. |
| `VARCHAR` | `VARCHAR` | Aurora MySQL up to 65,535 chars (subject to row size limit). |
| `NCHAR` | `CHAR` | No special UNICODE type — use `CHARACTER SET`/`COLLATE`. |
| `NVARCHAR` | `VARCHAR` | No special UNICODE type — use `CHARACTER SET`/`COLLATE`. |
| `DATE` | `DATE` | Aurora MySQL range 1000-01-01 to 9999-12-31 (no dates before 1000 AD). |
| `TIME` | `TIME` | Aurora MySQL no explicit fractional setting; up to 6 microsecond digits; range -838:59:59 to 838:59:59. Remove `TIME(n)`. |
| `SMALLDATETIME` | `DATETIME` / `TIMESTAMP` | Not supported — use `DATETIME`. |
| `DATETIME` | `DATETIME` | Aurora MySQL range 1000-01-01 to 9999-12-31, microsecond resolution. |
| `DATETIME2` | `DATETIME` | Aurora MySQL narrower range, lower (microsecond) resolution. |
| `DATETIMEOFFSET` | `TIMESTAMP` | No full time-zone awareness; use `time_zone` variable. `TIMESTAMP` range 1970-01-01 to 2038-01-19 (UTC stored). |
| `BINARY` | `BINARY` / `VARBINARY` | String data type, max 255 (use `VARBINARY` beyond). String literals, not `0x`. |
| `VARBINARY` | `VARBINARY` | Up to 65,535 chars. String literals, not `0x`. |
| `TEXT` / `VARCHAR(MAX)` | `VARCHAR` / `TEXT` / `MEDIUMTEXT` / `LONGTEXT` | Pick by length: 2^16-1 → VARCHAR/TEXT; 2^24-1 → MEDIUMTEXT; 2^32-1 → LONGTEXT. |
| `NTEXT` / `NVARCHAR(MAX)` | `VARCHAR` / `TEXT` / `MEDIUMTEXT` / `LONGTEXT` | No special UNICODE type — use `CHARACTER SET`/`COLLATE`. |
| `IMAGE` / `VARBINARY(MAX)` | `VARBINARY` / `BLOB` / `MEDIUMBLOB` / `LONGBLOB` | Pick by length similarly. |
| `CURSOR` | `CURSOR` | Not really a type in Aurora MySQL. |
| `UNIQUEIDENTIFIER` | N/A | Use `BINARY(16)` + `UUID()` function. |
| `HIERARCHYID` | N/A | Rewrite with adjacency list / nested set / closure table / materialized path. |
| `GEOMETRY` | `GEOMETRY` | Syntax/functionality differs significantly — rewrite required. |
| `TABLE` | N/A | No `TABLE` data type. |
| `XML` | N/A | No native XML — use `JSON` or string BLOBs. |
| `ROW_VERSION` | N/A | Use triggers to update a dedicated column. |
| `SQL_VARIANT` | N/A | Rewrite to use explicit types. |
