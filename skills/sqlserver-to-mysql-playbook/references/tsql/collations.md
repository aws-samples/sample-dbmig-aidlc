# Collations for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.collations.html

**Conversion category:** Assisted (Three star feature compatibility)
**SCT automation:** Four star automation level

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

Aurora MySQL supports multiple character sets and collations, defined separately (character set object + collation object). Supports 41 character sets and 222 collations; seven UNICODE character sets including UCS-2, UTF-8, UTF-32. Use UCS-2 for compatibility with SQL Server UNICODE types.

Collation levels: Server, Database, Table, Column, Expression (one more level — Table — than SQL Server).

View character sets: `INFORMATION_SCHEMA.CHARACTER_SETS` or `SHOW CHARACTER SET`. View collations: `INFORMATION_SCHEMA.COLLATIONS` or `SHOW COLLATION`.

Set server defaults via custom cluster parameter groups. Set session collation with `SET NAMES 'utf8';`. A *database* in Aurora MySQL equals a SQL Server *schema*.

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
_utf8'UNICODE String' COLLATE utf8_danish_ci;

-- view database default
SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME
FROM INFORMATION_SCHEMA.SCHEMATA
WHERE SCHEMA_NAME = '<Database Name>';
```

Change cluster character set/collation via RDS Parameter Groups: create a DB Cluster Parameter Group (family aurora-mysql5.7), edit `character_set_server` and `collation_server`, then apply to the cluster.

## Conversion notes

- UNICODE: replace `NCHAR`/`NVARCHAR` types with the `CHARACTER SET` property on a regular char type.
- Collation levels: SQL Server = Server/Database/Column/Expression; Aurora MySQL adds Table level.
- Metadata: `fn_helpcollations` → `INFORMATION_SCHEMA.SCHEMATA`, `SHOW COLLATION`, `SHOW CHARACTER SET`.
- Aurora MySQL uses an "introducer" prefix (e.g. `_utf8'...'`) to set a literal's character set without changing its value.
- Client apps should explicitly set character set/collation via `SET NAMES` / `SET CHARACTER SET` rather than relying on server defaults.

| Feature | SQL Server | Aurora MySQL |
|---|---|---|
| Unicode support | UTF-16 via `NCHAR`/`NVARCHAR` | 8 UNICODE character sets via `CHARACTER SET` option |
| Collation levels | Server, Database, Column, Expression | Server, Database, Table, Column, Expression |
| View collation metadata | `fn_helpcollation` | `INFORMATION_SCHEMA.SCHEMATA`, `SHOW COLLATION`, `SHOW CHARACTER SET` |
