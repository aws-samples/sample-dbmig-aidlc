# Data Types (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.datatypes.html

**Conversion category:** Assisted (Four-star compatibility, four-star automation)
**SCT automation:** SCT action code index: Data Types. SCT converts all incompatible data types. Key differences: syntax and handling differences.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): aligned with the toolkit `datatype-map.yaml` (`BIT`→`boolean`, `MONEY`→`numeric(19,4)`, `uuid`, `ltree`, PostGIS; verified), `uuidv7()` for `NEWSEQUENTIALID`, Babelfish availability on Aurora 18.

## SQL Server

Built-in data type categories:

| Category | Data types |
|---|---|
| Numeric | `BIT`, `TINYINT`, `SMALLINT`, `INT`, `BIGINT`, `NUMERIC`, `DECIMAL`, `MONEY`, `SMALLMONEY`, `FLOAT`, `REAL` |
| String/Character | `CHAR`, `VARCHAR`, `NCHAR`, `NVARCHAR` |
| Temporal | `DATE`, `TIME`, `SMALLDATETIME`, `DATETIME`, `DATETIME2`, `DATETIMEOFFSET` |
| Binary | `BINARY`, `VARBINARY` |
| LOB | `TEXT`, `NTEXT`, `IMAGE`, `VARCHAR(MAX)`, `NVARCHAR(MAX)`, `VARBINARY(MAX)` |
| Cursor | `CURSOR` |
| GUID | `UNIQUEIDENTIFIER` |
| Hierarchical | `HIERARCHYID` |
| Spatial | `GEOMETRY`, `GEOGRAPHY` |
| Sets (table type) | `TABLE` |
| XML | `XML` |
| Other | `ROWVERSION`, `SQL_VARIANT` |

`TEXT`, `NTEXT`, `IMAGE` are deprecated (use `VARCHAR(MAX)`, `NVARCHAR(MAX)`, `VARBINARY(MAX)`). AWS SCT converts `TEXT`/`NTEXT` → `BYTEA`/`LONGTEXT`, `IMAGE` → `BYTEA`/`LONGBLOB`.

Example:
```sql
CREATE TABLE MyTable
(
Col1 AS INTEGER NOT NULL PRIMARY KEY,
Col2 AS NVARCHAR(100) NOT NULL
);

DECLARE @MyXMLType AS XML,
  @MyTemporalType AS DATETIME2
```

## PostgreSQL

> **Toolkit mapping wins.** The authoritative mapping for this toolkit is `engines/sqlserver-to-postgresql/datatype-map.yaml`, which differs from the playbook tables below in several places: `BIT` → `boolean`, `MONEY`/`SMALLMONEY` → `numeric(19,4)`/`numeric(10,4)`, `UNIQUEIDENTIFIER` → `uuid`, `ROWVERSION` → `bytea`, `HIERARCHYID` → `ltree`, `GEOMETRY`/`GEOGRAPHY` → PostGIS. The playbook rows are kept for reference when reading SCT/DMS SC output.

**Character data types**

| SQL Server | Characteristic | Identical? | PostgreSQL |
|---|---|---|---|
| CHAR | Fixed length 1-8,000 | Yes | CHAR |
| VARCHAR | Variable length 1-8,000 | Yes | VARCHAR |
| NCHAR | Fixed length 1-4,000 | Yes | CHAR (n) |
| NVARCHAR | Variable length 1-4,000 | Yes | VARCHAR (n) |

**Numeric data types**

| SQL Server | Characteristic | Identical? | PostgreSQL |
|---|---|---|---|
| BIT | 1 byte per 8 BIT cols | No | `boolean` (toolkit default; `smallint` if the app treats it as 0/1). PostgreSQL `BIT` is a bit-string type, not a flag |
| TINYINT | 8-bit unsigned, 0-255 | No | SMALLINT |
| SMALLINT | 16-bit integer | Yes | SMALLINT |
| INT, INTEGER | 32-bit integer | Yes | INT, INTEGER |
| BIGINT | 64-bit integer | Yes | BIGINT |
| NUMERIC | Fixed-point | Yes | NUMERIC |
| DECIMAL | Fixed-point | Yes | DECIMAL |
| MONEY | 64-bit currency | No | `numeric(19,4)` (toolkit default). PostgreSQL `money` depends on `lc_monetary`, has fixed 2-decimal scale and is discouraged |
| SMALLMONEY | 32-bit currency | No | `numeric(10,4)` |
| FLOAT | Floating-point | Yes | FLOAT |
| REAL | Single-precision float | Yes | REAL |

**Temporal data types**

| SQL Server | Characteristic | Identical? | PostgreSQL |
|---|---|---|---|
| DATE | Date | Yes | DATE |
| TIME | Time | Yes | TIME |
| SMALLDATETIME | Date and time | No | TIMESTAMP(0) |
| DATETIME | Date+time with fraction | No | TIMESTAMP(3) |
| DATETIME2 | Date+time with fraction | No | TIMESTAMP(p) |
| DATETIMEOFFSET | Date+time+fraction+TZ | No | TIMESTAMP(p) WITH TIME ZONE |

**Binary data types**

| SQL Server | Characteristic | Identical? | PostgreSQL |
|---|---|---|---|
| BINARY | Fixed-length byte string | No | BYTEA |
| VARBINARY | Variable length 1-8,000 | No | BYTEA |

**LOB data types**

| SQL Server | Characteristic | Identical? | PostgreSQL |
|---|---|---|---|
| TEXT | Char data up to 2 GB | Yes | TEXT |
| NTEXT | Unicode UCS-2 up to 2 GB | No | TEXT |
| IMAGE | Char data up to 2 GB | No | BYTEA |
| VARCHAR(MAX) | Char data up to 2 GB | Yes | TEXT |
| NVARCHAR(MAX) | Unicode UCS-2 up to 2 GB | No | TEXT |
| VARBINARY(MAX) | Char data up to 2 GB | No | BYTEA |

**Spatial data types**

| SQL Server | Characteristic | Identical? | PostgreSQL |
|---|---|---|---|
| GEOMETRY | Euclidean (flat) coords | Yes | GEOMETRY |
| GEOGRAPHY | Round-earth coords | Yes | GEOGRAPHY |
| SQL_VARIANT | Max length 8016 | No | No equivalent |

**Other data types**

| SQL Server | Characteristic | Identical? | PostgreSQL |
|---|---|---|---|
| XML | XML data | Yes | XML |
| UNIQUEIDENTIFIER | 16-byte GUID (UUID) | No | `uuid`. `NEWID()` → `gen_random_uuid()`, `NEWSEQUENTIALID()` → `uuidv7()` (PG 18, time-ordered, verified). **Sort order differs**: SQL Server orders GUIDs by a special byte order, PostgreSQL by plain bytes |
| HIERARCHYID | ~5 bytes | No | `ltree` (available on Aurora 18, verified: ancestor tests with `@>`) when the app uses hierarchy methods; otherwise text/bytea |
| ROWVERSION | 8 bytes | No | `bytea` / `bigint` maintained by a trigger, or the `xmin` system column for optimistic concurrency. **Not** a timestamp |
| GEOMETRY / GEOGRAPHY | spatial | No | PostGIS `geometry` / `geography` (PostGIS 3.6 available on Aurora 18, verified) |

Character column semantics: PostgreSQL `VARCHAR(n)` stores n characters (not bytes), regardless of byte size of non-English characters.

SCT conversion example (SQL Server → PostgreSQL):
```sql
-- Source SQL Server
CREATE TABLE scttest(
SMALLDATETIMEcol SMALLDATETIME,
datetimecol DATETIME,
datetime2col DATETIME2,
datetimeoffsetcol DATETIMEOFFSET,
binarycol BINARY,
varbinarycol VARBINARY,
ntextcol NTEXT,
imagecol IMAGE,
nvarcharmaxcol NVARCHAR(MAX),
varbinarymaxcol VARBINARY(MAX),
uniqueidentifiercol UNIQUEIDENTIFIER,
hierarchyiDcol HIERARCHYID,
sql_variantcol SQL_VARIANT,
rowversioncol ROWVERSION);

-- AWS SCT output
CREATE TABLE scttest(
smalldatetimecol TIMESTAMP WITHOUT TIME ZONE,
datetimecol TIMESTAMP WITHOUT TIME ZONE,
datetime2col TIMESTAMP(6) WITHOUT TIME ZONE,
datetimeoffsetcol TIMESTAMP(6) WITH TIME ZONE,
binarycol BYTEA,
varbinarycol BYTEA,
ntextcol TEXT,
imagecol BYTEA,
nvarcharmaxcol TEXT,
varbinarymaxcol BYTEA,
uniqueidentifiercol UUID,
hierarchyidcol VARCHAR(8000),
sql_variantcol VARCHAR(8000),
rowversioncol VARCHAR(8000) NOT NULL);
```

## Conversion notes
- `TINYINT` → `SMALLINT` (PostgreSQL has no 8-bit unsigned type); add `CHECK (col BETWEEN 0 AND 255)` if the range matters.
- `MONEY`/`SMALLMONEY` → `numeric(19,4)`/`numeric(10,4)`, per the toolkit map. Avoid PostgreSQL `money`.
- `BIT` → `boolean`. Application code that writes `0`/`1` needs casts or must stay `smallint`; record the choice in `customer-specific/`.
- `DATETIME` rounds to 1/300 s ticks; PostgreSQL `timestamp(3)` is exact to the millisecond. Expect tiny differences in equivalence tests.
- All `BINARY`/`VARBINARY`/`IMAGE`/`VARBINARY(MAX)` → `BYTEA`.
- Temporal types map to `TIMESTAMP(p)` with/without time zone; `DATETIME`→`TIMESTAMP(3)`, `SMALLDATETIME`→`TIMESTAMP(0)`.
- `UNIQUEIDENTIFIER` → `uuid` (not `CHAR(16)`).
- `HIERARCHYID` → `ltree`, `ROWVERSION` → `bytea`/trigger/`xmin`, `SQL_VARIANT` → `text` (or `jsonb` to keep type info). SCT emits `VARCHAR(8000)` for all three, which loses behavior; redesign.
- **Babelfish alternative:** Aurora PostgreSQL 18 includes Babelfish (`babelfishpg_tsql` 6.2.0). It keeps SQL Server types (`money`, `datetime`, `uniqueidentifier`, `sql_variant`, …) and T-SQL over the TDS protocol. That is a different migration path from this toolkit's conversion; see `../tools/aws-sct.md`.
- `SQL_VARIANT` has no equivalent at all.
- Use proper collations/encoding when converting `TEXT`/`NTEXT`.
