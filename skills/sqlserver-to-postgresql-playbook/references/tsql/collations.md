# Collations

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.collations.html

**Conversion category:** Assisted (three-star feature compatibility)
**SCT automation:** No automation; SCT action code index: Collations

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): SQL Server CI/AI collation → ICU nondeterministic collation table (verified), PG 18 `LIKE` support, builtin provider, `citext`, fixed re-encode example, NCHAR alias behavior.

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
pg_dump -h <endpoint> -U <user> -f mydb1_export.sql mydb1
psql -c "ALTER DATABASE mydb1 RENAME TO mydb1_backup;"
psql -c "CREATE DATABASE mydb1 WITH ENCODING 'UTF8' TEMPLATE template0;"
PGCLIENTENCODING=OLD_DB_ENCODING psql -f mydb1_export.sql mydb1
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

### SQL Server collation → Aurora PostgreSQL 18 (verified on 18.6)

Aurora databases default to `UTF8` with libc `en_US.UTF-8`, which is **case- and accent-sensitive**. SQL Server's common defaults (`SQL_Latin1_General_CP1_CI_AS`, `Latin1_General_CI_AS`) are case-insensitive. Map them deliberately:

| SQL Server suffix | PostgreSQL 18 |
|---|---|
| `_CS_AS` / `_BIN2` | default deterministic collation; `"C"` or builtin `C.UTF-8` for binary (code-point) ordering |
| `_CI_AS` (case-insensitive, accent-sensitive) | `CREATE COLLATION ci (provider = icu, locale = 'und-u-ks-level2', deterministic = false);` |
| `_CI_AI` (case- and accent-insensitive) | `CREATE COLLATION ci_ai (provider = icu, locale = 'und-u-ks-level1', deterministic = false);` (verified: `'Café' = 'cafe'`) |
| language-specific (`Hungarian_100_…`, `Bengali_100_…`) | ICU locale (`'hu-HU'`, `'bn-BD'`) plus the strength option above |

Apply per column (`col text COLLATE ci`) or per database (`CREATE DATABASE … LOCALE_PROVIDER icu ICU_LOCALE 'und-u-ks-level2'` sets only the default sort order; database defaults must be deterministic, so case-insensitive **comparison** still needs column collations or `citext`).

- **PostgreSQL 18 supports `LIKE` with nondeterministic collations** (verified: `'Café' LIKE 'caf%' COLLATE ci_ai` is true). In PG ≤ 17 that raised an error, which was the main obstacle to using CI collations for SQL Server migrations.
- Nondeterministic collations still don't support pattern-index optimization for `LIKE 'abc%'` and are slower for equality than deterministic ones. For heavily searched columns, consider an expression index on `lower(col)` and rewriting predicates to `lower(col) = lower($1)`.
- `citext` (available on Aurora 18) is the simpler alternative for case-insensitive equality (not accent-insensitive).
- PostgreSQL 17+ also has the `builtin` provider (`C.UTF-8`, PG 18 `PG_UNICODE_FAST`) for fast, OS-independent binary ordering.
- Collation versions: after major upgrades check `pg_database_collation_actual_version()` and reindex text indexes if they changed. The `builtin` provider avoids this.

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
- `UTF16` storage is not supported. `NCHAR(n)`/`NATIONAL CHARACTER VARYING(n)` are accepted as aliases for `char(n)`/`varchar(n)`, but `NVARCHAR` is not a type name (verified). Map `NCHAR`/`NVARCHAR` to `CHAR`/`VARCHAR`/`TEXT` in a UTF-8 database; lengths are in characters, so `NVARCHAR(n)` → `varchar(n)` holds the same text.
- Collation can be set at column and expression level in both engines, but PostgreSQL uses locale names (e.g., `"de_DE"`) rather than SQL Server collation names.
- Changing a database's encoding requires a full dump/restore — plan for it during migration.
- PostgreSQL `CONVERSION` handles encoding translation, not SQL Server style data conversion.
