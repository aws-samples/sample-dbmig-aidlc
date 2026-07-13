# Character Sets and Encoding

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.charset.html

**Conversion category:** Assisted (Four-star feature compatibility, four-star automation)
**SCT automation:** N/A (action code index N/A)

## Oracle

Oracle supports most national/international encoded character set standards, with extensive Unicode support. Two scalar string-specific data types:

- **VARCHAR2** — variable-length strings, 1–4000 bytes; can store Unicode or non-Unicode.
- **NVARCHAR2** — stores Unicode data (AL16UTF16 or UTF8), specified at database creation.

Character sets are defined at the **instance level** (11g + 12cR1) or the **pluggable database level** (12cR2). Pre-12cR2, root container and all PDBs had to use identical character sets. Oracle 18c updates AL32UTF8 / AL16UTF16 to Unicode 9.0.

- **UTF8 Unicode**: Oracle uses AL32UTF8 — single-byte for Latin/ASCII, two bytes for some European/Middle-Eastern, three bytes for some South/East-Asian. Unicode storage requirements are generally higher than non-Unicode.
- **AL32UTF8** = UTF-8, valid as client and database charset. **AL16UTF16** = UTF-16BE, valid as national (NCHAR) charset.

Character set migration options:
- Export/Import from source Instance/PDB to a new Instance/PDB with a modified character set.
- Use the Database Migration Assistant for Unicode (DMU).
- The `CSALTER` utility is deprecated (since 2012).

View the database character set:
```sql
SELECT * FROM NLS_DATABASE_PARAMETERS;
```

## PostgreSQL

PostgreSQL supports many character sets (called **encodings**), single- and multi-byte. The default is set at cluster init (`initdb`); each database can have its own character set defined at creation.

Two implementation concepts:
- **Encoding** — basic rules for representing alphanumeric characters in binary (e.g. Unicode). Implemented at **database** level.
- **Locale** — superset incl. `LC_COLLATE` (sort order; must be a subset of the database encoding) and `LC_CTYPE` (classifies digit/letter/whitespace/punctuation). Implemented at **table-column** level.

Create a database with a specific encoding and locale:
```sql
CREATE DATABASE test01 WITH ENCODING 'EUC_KR' LC_COLLATE='ko_KR.euckr' LC_CTYPE='ko_KR.euckr' TEMPLATE=template0;
```

View configured character sets:
```sql
select datname, datcollate, datctype from pg_database;
-- or
select datname, pg_encoding_to_char(encoding), datcollate, datctype from pg_database;
```

**Collation version (Windows, PG 13+):** Starting with PostgreSQL 13 on Windows, collation version info is obtained from the OS. Prior to 13, `collversion` from `pg_collation` had no value reflecting OS collation version.
```sql
CREATE COLLATION german (provider = libc, locale = 'de_DE');
select oid,collname,collversion from pg_collation where collprovider='c' and collname='german';
-- PG 13: collversion shows e.g. 1539.5,1539.5
select pg_collation_actual_version (32769);
```

**Changing encoding** (no in-place modification supported): export, recreate, re-import.
```sql
pg_dump mydb1 > mydb1_export.sql
ALTER DATABASE mydb1 TO mydb1_backup;          -- rename or delete current db
CREATE DATABASE mydb1_new_encoding WITH ENCODING 'UNICODE' TEMPLATE=template0;
PGCLIENTENCODING=OLD_DB_ENCODING psql -f mydb1_export.sql mydb1_new_encoding
```
(`client_encoding` parameter overrides `PGCLIENTENCODING`.)

**Client/server conversions** (via `pg_conversion` catalog):
```sql
CREATE CONVERSION myconv FOR 'UTF8' TO 'LATIN1' FROM myfunc1;
psql \encoding SJIS
SET CLIENT_ENCODING TO 'value';
SHOW client_encoding;
RESET client_encoding;
```

**Table-level collation** (per-column sort/classification):
```sql
CREATE TABLE test1 (col1 text COLLATE "de_DE", col2 text COLLATE "es_ES");
```

## Conversion notes
- **No NCHAR/NVARCHAR in PostgreSQL** and **no UTF-16 support**. Oracle UTF16 (NVARCHAR2) has no PostgreSQL equivalent; Oracle UTF8 (VARCHAR2/NVARCHAR) maps to PostgreSQL `VARCHAR`.
- Character set granularity differs: Oracle = instance (11g/12cR1) or database (12cR2); PostgreSQL = database.
- Modifying a database character set in PostgreSQL requires full export → drop/rename → recreate with new charset → re-import (no in-place change). Oracle uses full Export/Import or the DMU utility for Unicode conversion.
- Some client-side-only characters cannot be used within the server.
- To fully comply with JSON spec and certain functions, set database encoding to UTF8.
