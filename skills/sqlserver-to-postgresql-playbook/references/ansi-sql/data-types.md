# Data Types (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.datatypes.html

**Conversion category:** Assisted (Four-star compatibility, four-star automation)
**SCT automation:** SCT action code index: Data Types. SCT converts all incompatible data types. Key differences: syntax and handling differences.

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
| BIT | 1 byte per 8 BIT cols | Yes | BIT |
| TINYINT | 8-bit unsigned, 0-255 | No | SMALLINT |
| SMALLINT | 16-bit integer | Yes | SMALLINT |
| INT, INTEGER | 32-bit integer | Yes | INT, INTEGER |
| BIGINT | 64-bit integer | Yes | BIGINT |
| NUMERIC | Fixed-point | Yes | NUMERIC |
| DECIMAL | Fixed-point | Yes | DECIMAL |
| MONEY | 64-bit currency | Yes | MONEY |
| SMALLMONEY | 32-bit currency | No | MONEY |
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
| UNIQUEIDENTIFIER | 16-byte GUID (UUID) | No | CHAR(16) |
| HIERARCHYID | ~5 bytes | No | VARCHAR (n) |
| ROWVERSION | 8 bytes | No | TIMESTAMP(p) |

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
- `TINYINT` → `SMALLINT` (PostgreSQL has no 8-bit unsigned type).
- `SMALLMONEY` → `MONEY`.
- All `BINARY`/`VARBINARY`/`IMAGE`/`VARBINARY(MAX)` → `BYTEA`.
- Temporal types map to `TIMESTAMP(p)` with/without time zone; `DATETIME`→`TIMESTAMP(3)`, `SMALLDATETIME`→`TIMESTAMP(0)`.
- `UNIQUEIDENTIFIER` → `UUID` (table maps it to `CHAR(16)`, but SCT example emits `UUID`).
- `HIERARCHYID`, `SQL_VARIANT`, `ROWVERSION` have no real equivalents — SCT emits `VARCHAR(8000)`; redesign for proper functionality.
- `SQL_VARIANT` has no equivalent at all.
- Use proper collations/encoding when converting `TEXT`/`NTEXT`.
