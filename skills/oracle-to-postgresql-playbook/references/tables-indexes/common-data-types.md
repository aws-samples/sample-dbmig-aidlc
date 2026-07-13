# Common Oracle and PostgreSQL Data Types

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.common.html

**Conversion category:** Automatic (four-star feature compatibility, four-star automation)
**SCT automation:** Data Types action code index. AWS SCT automatically converts most data types; manual action recommended for `BFILE`, `ROWID`, `UROWID`.

## Oracle
Oracle provides primitive data types for table columns and PL/SQL variables. The assigned data type defines valid values for each column/argument.

**Character types**

| Oracle | Characteristic | PG identical? | PostgreSQL type |
|---|---|---|---|
| CHAR(n) | Max 2000 bytes | Yes | CHAR(n) |
| CHARACTER(n) | Max 2000 bytes | Yes | CHARACTER(n) |
| NCHAR(n) | Max 2000 bytes | No | CHAR(n) |
| VARCHAR(n) | Max 2000 bytes | Yes | VARCHAR(n) |
| NCHAR VARYING(n) | UTF-8, max 4000 bytes | No | CHARACTER VARYING(n) |
| VARCHAR2(n) 11g | Max 4000 bytes (32KB in PL/SQL) | No | VARCHAR(n) |
| VARCHAR2(n) 12g | Max 32767 bytes, MAX_STRING_SIZE=EXTENDED | No | VARCHAR(n) |
| NVARCHAR2(n) | Max 4000 bytes | No | VARCHAR(n) |
| LONG | Max 2GB | No | TEXT |
| RAW(n) | Max 2000 bytes | No | BYTEA |
| LONG RAW | Max 2GB | No | BYTEA |

**Numeric types**

| Oracle | Characteristic | PG identical? | PostgreSQL type |
|---|---|---|---|
| NUMBER | Floating-point | No | DOUBLE PRECISION |
| NUMBER(*) | Floating-point | No | DOUBLE PRECISION |
| NUMBER(p,s) | p 1–38, s -84–127 | No | DECIMAL(p,s) |
| NUMERIC(p,s) | p 1–38 | Yes | NUMERIC(p,s) |
| FLOAT(p) | Floating-point | No | DOUBLE PRECISION |
| DEC(p,s) | Fixed-point | Yes | DEC(p,s) |
| DECIMAL(p,s) | Fixed-point | Yes | DECIMAL(p,s) |
| INT | 38-digit integer | Yes | INTEGER or NUMERIC(38,0) |
| INTEGER | 38-digit integer | Yes | INTEGER or NUMERIC(38,0) |
| SMALLINT | 38-digit integer | Yes | SMALLINT |
| REAL | Floating-point | No | DOUBLE PRECISION |
| DOUBLE PRECISION | Floating-point | Yes | DOUBLE PRECISION |

**Date/time types**

| Oracle | Characteristic | PG identical? | PostgreSQL type |
|---|---|---|---|
| DATE | Date + time (y,mo,d,h,mi,s) | Yes | TIMESTAMP(0) |
| TIMESTAMP(p) | Date+time with fraction | Yes | TIMESTAMP(p) |
| TIMESTAMP(p) WITH TIME ZONE | + time zone | Yes | TIMESTAMP(p) WITH TIME ZONE |
| INTERVAL YEAR(p) TO MONTH | Date interval | Yes | INTERVAL YEAR TO MONTH |
| INTERVAL DAY(p) TO SECOND(s) | Day/time interval | Yes | INTERVAL DAY TO SECOND(s) |

**LOB types**

| Oracle | Characteristic | PG identical? | PostgreSQL type |
|---|---|---|---|
| BFILE | Pointer to binary file, max 4GB | No | VARCHAR(255) / CHARACTER VARYING(255) |
| BLOB | Binary large object, max 4GB | No | BYTEA |
| CLOB | Character large object, max 4GB | No | TEXT |
| NCLOB | Variable-length Unicode, max 4GB | No | TEXT |

**ROWID types**

| Oracle | Characteristic | PG identical? | PostgreSQL type |
|---|---|---|---|
| ROWID | Physical row address | No | CHARACTER(255) |
| UROWID(n) | Universal/logical row id | No | CHARACTER VARYING |

**Other types**

| Oracle | PostgreSQL type |
|---|---|
| XMLTYPE | XML |
| BOOLEAN (PL/SQL only, can't be a table column) | BOOLEAN |
| SDO_GEOMETRY, SDO_TOPO_GEOMETRY, SDO_GEORASTER (spatial) | N/A |
| ORDDicom, ORDDoc, ORDImage, ORDVideo (media) | N/A |

> The "PostgreSQL identical compatibility" column indicates whether the exact Oracle data type syntax can be used when migrating to Aurora PostgreSQL.

### Oracle character column semantics
Oracle supports both `BYTE` and `CHAR` semantics for `CHAR`/`VARCHAR` column sizing:
- `VARCHAR2(10 BYTE)` — up to 10 bytes of storage (may hold fewer than 10 multi-byte chars).
- `VARCHAR2(10 CHAR)` — exactly 10 characters regardless of bytes.

```sql
CREATE TABLE table1 (col1 VARCHAR2(10 CHAR), col2 VARCHAR2(10 BYTE));
```

Default is `BYTE`. For multi-byte charsets (e.g. UTF8), use the `CHAR` modifier or change `NLS_LENGTH_SEMANTICS`:

```sql
ALTER system SET nls_length_semantics=char scope=both;
ALTER session SET nls_length_semantics=char;
```

## PostgreSQL
PostgreSQL offers equivalents for most Oracle types. Notable PostgreSQL types: CHAR/CHARACTER/CHAR(n), VARCHAR(n), TEXT; NUMERIC(p,s), REAL, DOUBLE PRECISION, INT/INTEGER, SMALLINT, BIGINT, BIT, BIT VARYING, MONEY (discouraged); TIMESTAMP, INTERVAL, DATE, TIME; BOOLEAN; XML; geometric types POINT/LINE/LSEG/BOX/PATH/POLYGON/CIRCLE; plus JSON, JSONB, SERIAL, OID, CIDR, INET, MACADDR, MACADDR8, PG_LSN, BYTEA, TSQUERY, TSVECTOR, TXID_SNAPSHOT, UUID.

### PostgreSQL character column semantics
PostgreSQL only supports `CHAR` (character) semantics. `VARCHAR(10)` stores 10 characters regardless of bytes per character — `VARCHAR(n)` is n characters, not bytes.

### AWS SCT migration example
Source Oracle `DATATYPES` table:

```sql
CREATE TABLE "DATATYPES"(
  "BFILE"                    BFILE,
  "BINARY_FLOAT"             BINARY_FLOAT,
  "BINARY_DOUBLE"            BINARY_DOUBLE,
  "BLOB"                     BLOB,
  "CHAR"                     CHAR(10 BYTE),
  "CHARACTER"                CHAR(10 BYTE),
  "CLOB"                     CLOB,
  "NCLOB"                    NCLOB,
  "DATE"                     DATE,
  "DECIMAL"                  NUMBER(3,2),
  "DEC"                      NUMBER(3,2),
  "DOUBLE_PRECISION"         FLOAT(126),
  "FLOAT"                    FLOAT(3),
  "INTEGER"                  NUMBER(*,0),
  "INT"                      NUMBER(*,0),
  "INTERVAL_YEAR"            INTERVAL YEAR(4) TO MONTH,
  "INTERVAL_DAY"             INTERVAL DAY(4) TO SECOND(4),
  "LONG"                     LONG,
  "NCHAR"                    NCHAR(10),
  "NCHAR_VARYING"            NVARCHAR2(10),
  "NUMBER"                   NUMBER(9,9),
  "NUMBER1"                  NUMBER(9,0),
  "NUMBER(*)"                NUMBER,
  "NUMERIC"                  NUMBER(9,9),
  "NVARCHAR2"                NVARCHAR2(10),
  "RAW"                      RAW(10),
  "REAL"                     FLOAT(63),
  "ROW_ID"                   ROWID,
  "SMALLINT"                 NUMBER(*,0),
  "TIMESTAMP"                TIMESTAMP(5),
  "TIMESTAMP_WITH_TIME_ZONE" TIMESTAMP(5) WITH TIME ZONE,
  "UROWID"                   UROWID(10),
  "VARCHAR"                  VARCHAR2(10 BYTE),
  "VARCHAR2"                 VARCHAR2(10 BYTE),
  "XMLTYPE"                  XMLTYPE
);
```

Target PostgreSQL table converted by AWS SCT:

```sql
CREATE TABLE IF NOT EXISTS datatypes(
bfile                    character varying(255) DEFAULT NULL,
binary_float             real DEFAULT NULL,
binary_double            double precision DEFAULT NULL,
blob                     bytea DEFAULT NULL,
char                     character(10) DEFAULT NULL,
character                character(10) DEFAULT NULL,
clob                     text DEFAULT NULL,
nclob                    text DEFAULT NULL,
date                     TIMESTAMP(0) without time zone DEFAULT NULL,
decimal                  numeric(3,2) DEFAULT NULL,
dec                      numeric(3,2) DEFAULT NULL,
double_precision         double precision DEFAULT NULL,
float                    double precision DEFAULT NULL,
integer                  numeric(38,0) DEFAULT NULL,
int                      numeric(38,0) DEFAULT NULL,
interval_year            interval year to month(6) DEFAULT NULL,
interval_day             interval day to second(4) DEFAULT NULL,
long                     text DEFAULT NULL,
nchar                    character(10) DEFAULT NULL,
nchar_varying            character varying(10) DEFAULT NULL,
number                   numeric(9,9) DEFAULT NULL,
number1                  numeric(9,0) DEFAULT NULL,
"number(*)"              double precision DEFAULT NULL,
numeric                  numeric(9,9) DEFAULT NULL,
nvarchar2                character varying(10) DEFAULT NULL,
raw                      bytea DEFAULT NULL,
real                     double precision DEFAULT NULL,
row_id                   character(255) DEFAULT NULL,
smallint                 numeric(38,0) DEFAULT NULL,
timestamp                TIMESTAMP(5) without time zone DEFAULT NULL,
timestamp_with_time_zone TIMESTAMP(5) with time zone DEFAULT NULL,
urowid                   character varying DEFAULT NULL,
varchar                  character varying(10) DEFAULT NULL,
varchar2                 character varying(10) DEFAULT NULL,
xmltype                  xml DEFAULT NULL
)
WITH (
OIDS=FALSE
);
```

## Conversion notes
- PostgreSQL does **not** support `BFILE`, `ROWID`, `UROWID` — AWS SCT raises manual-action flags.
- **BFILE**: pointers to binary files. Either store a named file + a routine that fetches it from the filesystem, or store the blob inside the database.
- **ROWID**: physical row addresses. PostgreSQL has a `ctid` system column (physical row-version location) but no comparable data type; use `CHAR` as a partial equivalent. Code using ROWID may need modification.
- **UROWID**: supports logical/physical rowids including foreign (non-Oracle) table rowids via gateway. No equivalent; use `VARCHAR(n)` as a partial equivalent. Code using UROWID may need modification.
- `NUMBER`/`NUMBER(*)`/`FLOAT(p)`/`REAL` map to `DOUBLE PRECISION` (not bit-identical to Oracle's variable-precision NUMBER).
- Oracle `DATE` includes a time component → maps to `TIMESTAMP(0)`, not PostgreSQL `DATE`.
- Watch BYTE vs CHAR semantics: a `VARCHAR2(n BYTE)` column may need a larger length in PostgreSQL (which is char-based) when multi-byte data is involved.
