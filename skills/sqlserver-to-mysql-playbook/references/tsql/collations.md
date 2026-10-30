# Collations for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.collations.html

**Conversion category:** Assisted (Three star feature compatibility)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): utf8mb4 instead of UCS-2/utf8 (corrected); verified SQL Server → MySQL collation mapping table, NO PAD vs PAD SPACE trailing-space behavior, accent-insensitive default, NCHAR = utf8mb3.

## SQL Server

SQL Server collations define rules for string storage and comparison: sorting, case sensitivity, accent sensitivity, and code page mapping. Supports both ASCII and UCS-2 UNICODE data. UNICODE uses dedicated `N`-prefixed types: `NCHAR` and `NVARCHAR` (ASCII counterparts are `CHAR`/`VARCHAR`). UNICODE and non-UNICODE types are not compatible; conflicts resolve via collation precedence rules.

Collations control sensitivity for: Case, Accent, Kana, Width, Variation selector. Suffix naming appends options, e.g. `Azeri_Cyrillic_100_CS_AS_KS_WS_SC`.

Three collation set types: Windows Collations, Binary Collations, SQL Server Collations (backward compatibility).

Collation levels: Server, Database, Column, Expression. SQL Server supports UCS-2 UNICODE only; SQL Server 2019 adds UTF-8 for import/export and as DB/column-level collation.

View collations: `SELECT * FROM sys.fn_helpcollations()`.

### Syntax

```sql
CREATE DATABASE <Database Name>
[ ON <File Specifications> ]
COLLATE <Collation>
[ WITH <Database Option List> ];

CREATE TABLE <Table Name>
(
    <Column Name> <String Data Type>
    COLLATE <Collation> [ <Column Constraints> ]...
);
```

### Examples

```sql
CREATE DATABASE MyBengaliDatabase
ON
( NAME = MyBengaliDatabase_Datafile,
    FILENAME = 'C:\Program Files\Microsoft SQL Server\MSSQL13.MSSQLSERVER\MSSQL\DATA\MyBengaliDatabase.mdf',
    SIZE = 100)
LOG ON
    ( NAME = MyBengaliDatabase_Logfile,
FILENAME = 'C:\Program Files\Microsoft SQL Server\MSSQL13.MSSQLSERVER\MSSQL\DATA\MyBengaliDblog.ldf',
    SIZE = 25)
COLLATE Bengali_100_CS_AI;

CREATE TABLE MyTable
(
    Col1 CHAR(10) COLLATE Hungarian_100_CI_AI_SC NOT NULL PRIMARY KEY,
    COL2 VARCHAR(100) COLLATE Sami_Sweden_Finland_100_CS_AS_KS NOT NULL
);
```

## MySQL

Aurora MySQL supports multiple character sets and collations, defined separately (character set object + collation object). *(corrected)* Use **`utf8mb4`** — the Aurora 3 / 8.4 server default (`utf8mb4_0900_ai_ci`, verified) — for all SQL Server `NCHAR`/`NVARCHAR` and `VARCHAR` data; UCS-2 (recommended by the original) cannot be a client character set and is not needed.

Collation levels: Server, Database, Table, Column, Expression (one more level — Table — than SQL Server).

View character sets: `INFORMATION_SCHEMA.CHARACTER_SETS` or `SHOW CHARACTER SET`. View collations: `INFORMATION_SCHEMA.COLLATIONS` or `SHOW COLLATION`.

Set server defaults via custom cluster parameter groups. Set session character set with `SET NAMES utf8mb4;` (`utf8` is the deprecated alias of the 3-byte `utf8mb3`). A *database* in Aurora MySQL equals a SQL Server *schema*.

### Syntax

```sql
-- database-level
CREATE DATABASE <Database Name>
[DEFAULT] CHARACTER SET <Character Set>
[[DEFAULT] COLLATE <Collation>];

-- table-level
CREATE TABLE <Table Name>
(Column Specifications)
[DEFAULT] CHARACTER SET <Character Set>
[COLLATE <Collation>];

-- column-level
CREATE TABLE <Table Name>
(
<Column Name> {CHAR | VARCHAR | TEXT} (<Length>)
CHARACTER SET <Character Set>
[COLLATE <Collation>]);

-- expression-level
_<Character Set>'<String>' COLLATE <Collation>
```

### Examples

```sql
CREATE DATABASE MyDatabase
CHARACTER SET latin1 COLLATE latin1_swedish_ci;

CREATE TABLE MyTable
(
    StringColumn VARCHAR(5) NOT NULL
    CHARACTER SET latin1
    COLLATE latin1_german1_ci
);

-- expression level with introducer prefix
SELECT _latin1'Latin non-UNICODE String',
_utf8mb4'UNICODE String' COLLATE utf8mb4_danish_ci;

-- view database default
SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME
FROM INFORMATION_SCHEMA.SCHEMATA
WHERE SCHEMA_NAME = '<Database Name>';
```

Change cluster character set/collation via RDS Parameter Groups: create a DB Cluster Parameter Group (family `aurora-mysql8.4` or `aurora-mysql8.0`), edit `character_set_server` and `collation_server`, then apply to the cluster.

### Mapping SQL Server collations (verified on Aurora MySQL 3.13 and 8.4.8)

| SQL Server | Aurora MySQL | Behavior check |
|---|---|---|
| `SQL_Latin1_General_CP1_CI_AS`, `Latin1_General_CI_AS` (case-insensitive, accent-sensitive) | `utf8mb4_0900_as_ci` | `'é' = 'e'` → 0, case-insensitive |
| `…_CI_AI` | `utf8mb4_0900_ai_ci` (the default) | `'é' = 'e'` → 1 |
| `…_CS_AS` | `utf8mb4_0900_as_cs` | case- and accent-sensitive |
| `…_BIN`, `…_BIN2` | `utf8mb4_bin` | binary order |

- **Trailing spaces:** SQL Server ignores trailing spaces in `=` comparisons. MySQL `_0900_` collations are **NO PAD**: `'a ' = 'a'` → 0; the older `utf8mb4_unicode_ci` / `utf8mb4_general_ci` collations are PAD SPACE (`'a ' = 'a'` → 1) (all verified). Choose a PAD SPACE collation, or `RTRIM` on load, where application code depends on SQL Server's behavior — and note that unique keys then also treat `'a'` and `'a '` as equal.
- The default `_ai_ci` collation is **accent-insensitive**, unlike SQL Server's usual `_AS`: unique keys on names (`José` vs `Jose`) can collide after migration. Use `utf8mb4_0900_as_ci` for such columns.
- MySQL `NCHAR`/`NVARCHAR` column types mean `utf8mb3` and reject 4-byte characters (error 1366, verified) — map SQL Server national types to `CHAR`/`VARCHAR` with `utf8mb4`.

## Conversion notes

- UNICODE: replace `NCHAR`/`NVARCHAR` types with `CHAR`/`VARCHAR` in `utf8mb4` (never MySQL `NCHAR`, which is `utf8mb3`).
- Collation levels: SQL Server = Server/Database/Column/Expression; Aurora MySQL adds Table level.
- Metadata: `fn_helpcollations` → `INFORMATION_SCHEMA.SCHEMATA`, `SHOW COLLATION`, `SHOW CHARACTER SET`.
- Aurora MySQL uses an "introducer" prefix (e.g. `_utf8'...'`) to set a literal's character set without changing its value.
- Client apps should explicitly set character set/collation via `SET NAMES` / `SET CHARACTER SET` rather than relying on server defaults.

| Feature | SQL Server | Aurora MySQL |
|---|---|---|
| Unicode support | UTF-16 via `NCHAR`/`NVARCHAR` | 8 UNICODE character sets via `CHARACTER SET` option |
| Collation levels | Server, Database, Column, Expression | Server, Database, Table, Column, Expression |
| View collation metadata | `fn_helpcollation` | `INFORMATION_SCHEMA.SCHEMATA`, `SHOW COLLATION`, `SHOW CHARACTER SET` |
