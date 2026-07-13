# Collations

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.collations.html

**Conversion category:** Assisted (three-star feature compatibility)
**SCT automation:** No automation; SCT action code index: Collations

## SQL Server

Collations define rules for string storage and management: sorting, case sensitivity, accent sensitivity, and code page mapping. SQL Server supports ASCII and UCS-2 UNICODE. UNICODE types use the `N` prefix (`NCHAR`, `NVARCHAR`); ASCII counterparts are `CHAR`/`VARCHAR`. UNICODE and non-UNICODE types are not compatible; conflicts are resolved via collation precedence rules.

View supported collations:

```sql
SELECT * FROM sys.fn_helpcollations()
```

Collation sensitivity covers: Case, Accent, Kana, Width, Variation selector. The suffix naming convention appends options (e.g., `Azeri_Cyrillic_100_CS_AS_KS_WS_SC` = case/accent/kana/width-sensitive + supplementary characters).

Three collation set types: **Windows collations** (OS locale rules), **Binary collations** (bit-wise, locale-independent), and **SQL Server collations** (backward compatibility).

Collation levels:
- **Server-level**: default for system + future user databases.
- **Database-level**: inherits server default unless `CREATE DATABASE` overrides; default for `CREATE/ALTER TABLE`.
- **Column-level**: override via `CREATE/ALTER TABLE`.
- **Expression-level**: via `COLLATE` function, e.g. `SELECT * FROM MyTable ORDER BY StringColumn COLLATE Latin1_General_CS_AS`.

SQL Server supports UCS-2 only. SQL Server 2019 adds UTF-8 for import/export and as DB/column collation.

Syntax:

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

Examples:

```sql
CREATE DATABASE MyBengaliDatabase
ON ( NAME = MyBengaliDatabase_Datafile,
  FILENAME = '...MyBengaliDatabase.mdf', SIZE = 100)
LOG ON ( NAME = MyBengaliDatabase_Logfile,
  FILENAME = '...MyBengaliDblog.ldf', SIZE = 25)
COLLATE Bengali_100_CS_AI;

CREATE TABLE MyTable
(
Col1 CHAR(10) COLLATE Hungarian_100_CI_AI_SC NOT NULL PRIMARY KEY,
COL2 VARCHAR(100) COLLATE Sami_Sweden_Finland_100_CS_AS_KS NOT NULL
);
```

## PostgreSQL

PostgreSQL supports many character sets (encodings), single- and multi-byte. The default is set at cluster init (`initdb`); each database can set its own encoding at creation. PostgreSQL does **not** natively support `NVARCHAR` or UTF-16.

Concepts:
- **Encoding** — rules for representing characters in binary (e.g., Unicode). Level: Database.
- **Locale** — superset including `LC_COLLATE` (sort order) and `LC_CTYPE`; must be a subset of the database encoding. Level: Table/Column.

Examples:

```sql
-- Create DB with Korean encoding/locale:
CREATE DATABASE test01 WITH ENCODING 'EUC_KR' LC_COLLATE='ko_KR.euckr' LC_CTYPE='ko_KR.euckr' TEMPLATE=template0;

-- View per-database character sets:
select datname, datcollate, datctype from pg_database;
```

**Changing encoding** is not supported in place — export, recreate, re-import:

```bash
pg_dump mydb1 > mydb1_export.sql
```
```sql
ALTER DATABASE mydb1 TO mydb1_backup;
CREATE DATABASE mydb1_new_encoding WITH ENCODING 'UNICODE' TEMPLATE=template0;
```
```bash
PGCLIENTENCODING=OLD_DB_ENCODING psql -f mydb1_export.sql mydb1_new_encoding
```

**Custom conversion** and client encoding:

```sql
CREATE CONVERSION myconv FOR 'UTF8' TO 'LATIN1' FROM myfunc1;
-- client encoding:
SET CLIENT_ENCODING TO 'value';   -- or:  \encoding SJIS
SHOW client_encoding;
RESET client_encoding;
```

**Column-level collation:**

```sql
CREATE TABLE test1 (col1 text COLLATE "de_DE", col2 text COLLATE "es_ES");
```

For RDS PostgreSQL 13+ on Windows, collation version info is now available from the OS (`pg_collation_actual_version`).

## Summary

| Feature | SQL Server | Aurora PostgreSQL |
|---|---|---|
| View database character set | `SELECT collation_name FROM sys.databases;` | `select datname, pg_encoding_to_char(encoding), datcollate, datctype from pg_database;` |
| Modify database character set | Recreate the database | Export → drop/rename → recreate with new charset → import |
| Character set granularity | Database | Database |
| UTF8 | Supported | Supported |
| UTF16 | Supported | Not Supported |
| `NCHAR` / `NVARCHAR` | Supported | Not Supported |

## Conversion notes
- `UTF16`, `NCHAR`, and `NVARCHAR` are not supported — map `NCHAR`/`NVARCHAR` to `CHAR`/`VARCHAR`/`TEXT` with UTF-8 encoding.
- Collation can be set at column and expression level in both engines, but PostgreSQL uses locale names (e.g., `"de_DE"`) rather than SQL Server collation names.
- Changing a database's encoding requires a full dump/restore — plan for it during migration.
- PostgreSQL `CONVERSION` handles encoding translation, not SQL Server style data conversion.
