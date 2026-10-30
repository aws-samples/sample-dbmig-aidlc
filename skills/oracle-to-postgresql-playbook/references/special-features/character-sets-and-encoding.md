# Character Sets and Encoding

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.charset.html

**Conversion category:** Assisted (Four-star feature compatibility, four-star automation)
**SCT automation:** N/A (action code index N/A)

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): added the PG 17/18 locale providers (builtin, ICU) and their sort-order impact versus Oracle `NLS_SORT`, case-insensitive collations with PG 18 `LIKE` support, NCHAR syntax behavior (verified), and fixed the re-encode example.

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

**Locale providers (Aurora PostgreSQL 18, verified on 18.6).** Aurora databases default to encoding `UTF8` with libc locale `en_US.UTF-8`. Three providers are available when you create a database or collation:

| Provider | Use for | Example |
|---|---|---|
| `libc` | Default; OS (glibc) collations | `CREATE DATABASE app TEMPLATE template0 ENCODING 'UTF8' LOCALE 'en_US.UTF-8';` |
| `icu` | Language-aware sorting matching Oracle linguistic sorts (`NLS_SORT`), case/accent-insensitive collations | `CREATE DATABASE app TEMPLATE template0 ENCODING 'UTF8' LOCALE_PROVIDER icu ICU_LOCALE 'en-US';` |
| `builtin` (PG 17+) | Fast, stable code-point ordering like Oracle `NLS_SORT=BINARY`; `C.UTF-8` and `PG_UNICODE_FAST` (PG 18) | `CREATE DATABASE app TEMPLATE template0 ENCODING 'UTF8' LOCALE_PROVIDER builtin BUILTIN_LOCALE 'C.UTF-8';` |

Choosing the order matters for converted queries: Oracle's default `NLS_SORT=BINARY` sorts `'B'` before `'a'`. The PostgreSQL `C` / builtin collations match that, while `en_US` / ICU collations do not (verified: `'a' < 'B'` is false under `"C"` and true under `"en-US-x-icu"`). Decide per database and record it, because `ORDER BY` results, range predicates and `MIN`/`MAX` on text change with the collation.

**Case-insensitive comparison (Oracle `NLS_COMP=LINGUISTIC`, `NLS_SORT=BINARY_CI`)** → a nondeterministic ICU collation. PostgreSQL 18 also supports `LIKE` with nondeterministic collations (verified):
```sql
CREATE COLLATION ci (provider = icu, locale = 'und-u-ks-level2', deterministic = false);
SELECT 'ABC' = 'abc' COLLATE ci;        -- true
SELECT 'ABC' LIKE 'a%' COLLATE ci;       -- true (PG 18+)
```
Indexes on nondeterministic collations support equality, but not pattern prefix optimization.

**Collation versions:** libc and ICU collation definitions can change with OS/ICU upgrades, which can corrupt indexes on text. Aurora manages the OS. After major upgrades, check `SELECT datname, datcollversion, pg_database_collation_actual_version(oid) FROM pg_database;` and `REINDEX` text indexes if the versions differ. The `builtin` provider avoids this risk.

**Changing encoding** (no in-place modification supported): export, recreate, re-import.
```bash
pg_dump -h <endpoint> -U <user> -f mydb1_export.sql mydb1
psql -c "ALTER DATABASE mydb1 RENAME TO mydb1_backup;"          # or drop it
psql -c "CREATE DATABASE mydb1 WITH ENCODING 'UTF8' TEMPLATE template0;"
PGCLIENTENCODING=OLD_DB_ENCODING psql -f mydb1_export.sql mydb1
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
- **No separate national character types and no UTF-16 storage.** PostgreSQL accepts `NCHAR(n)` and `NATIONAL CHARACTER VARYING(n)` as syntax, but they become ordinary `character(n)` / `character varying(n)` (verified). `NVARCHAR` is not a type name. With a `UTF8` database every string type stores any Unicode character, so map Oracle `NVARCHAR2(n)` → `varchar(n)` and `NCHAR(n)` → `char(n)`.
- **Length semantics:** PostgreSQL `varchar(n)` counts **characters**, like Oracle `VARCHAR2(n CHAR)`. Oracle `VARCHAR2(n BYTE)` (the common default) can therefore hold more multibyte text after conversion. That is safe, but if exact byte limits matter, add `CHECK (octet_length(col) <= n)`.
- Oracle `AL32UTF8` → create the Aurora database with `ENCODING 'UTF8'` (the default). Pick the collation deliberately (see the table above).
- Character set granularity differs: Oracle = instance (11g/12cR1) or database (12cR2); PostgreSQL = database.
- Modifying a database character set in PostgreSQL requires full export → drop/rename → recreate with new charset → re-import (no in-place change). Oracle uses full Export/Import or the DMU utility for Unicode conversion.
- Some client-side-only characters cannot be used within the server.
- To fully comply with JSON spec and certain functions, set database encoding to UTF8.
