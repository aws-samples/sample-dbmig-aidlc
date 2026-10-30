# Oracle and MySQL Character Sets

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.charset.html

**Conversion category:** Automatic (four-star feature compatibility; four-star automation)
**SCT automation:** N/A — handled automatically; main difference is syntax and that MySQL allows different collations per database in the same instance.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected the initdb (PostgreSQL) reference and the ucs2 example; verified utf8mb4/utf8mb4_0900_ai_ci defaults, NCHAR/NVARCHAR = utf8mb3 (rejects 4-byte characters), accent/case-insensitive default collation, CONVERT TO for existing tables.

## Oracle

Oracle supports national and international encoded character set standards including extensive Unicode support. Two scalar string types:

- `VARCHAR2` — variable-length strings, 1–4000 bytes; can store Unicode or non-Unicode depending on database config.
- `NVARCHAR2` — Unicode-only; supports AL16UTF16 or UTF8, specified at database creation.

Character sets are defined at the instance level (11g) or pluggable-database level (12c R2). Pre-12cR2, the root container and all PDBs had to share the same character set.

- UTF-8 supported via AL32UTF8 (single-byte for Latin, two-byte for some European/Middle-Eastern, three-byte for some South/East-Asian); valid as client and database character set.
- UTF-16BE supported via AL16UTF16; valid as the national (NCHAR) character set.

View the database character set:

```sql
SELECT * FROM NLS_DATABASE_PARAMETERS;
```

Character set migration options:
- Full export/import from source instance/PDB to a new instance/PDB with a modified character set.
- Database Migration Assistant for Unicode (DMU) when converting to Unicode.
- `CSALTER` is deprecated (as of 2012).

## MySQL

MySQL supports many single-byte and multi-byte character sets. On Aurora MySQL 3 and 8.4 the server default is **`utf8mb4` with collation `utf8mb4_0900_ai_ci`** (verified; set `character_set_server`/`collation_server` in the DB cluster parameter group to change it). Each database, table and column can define its own character set. (The original text mentioned `initdb`, which is a PostgreSQL tool.) Query available sets with the `INFORMATION_SCHEMA.CHARACTER_SETS` table or `SHOW CHARACTER SET`; query collations with `INFORMATION_SCHEMA.COLLATIONS` or `SHOW COLLATION`.

Collation characteristics: two different character sets cannot share a collation; each character set has a default collation; collation names start with the character set name plus suffixes.

Create a database using Korean EUC-KR:

```sql
CREATE DATABASE test01 CHARACTER SET = euckr COLLATE = euckr_korean_ci;
```

View per-database character sets:

```sql
SELECT SCHEMA_NAME,
       DEFAULT_CHARACTER_SET_NAME,
       DEFAULT_COLLATION_NAME
FROM INFORMATION_SCHEMA.SCHEMATA;
```

Convert a character set / collation:

```sql
ALTER DATABASE test01 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_as_cs;
-- changes only the DEFAULT for new tables; convert existing tables explicitly:
ALTER TABLE t CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs;
```

Per-column character set / collation (granularity Oracle does not offer):

```sql
CREATE TABLE lang(
  latin1_col CHAR(10) CHARACTER SET latin1 COLLATE latin1_german1_ci,
  latin2_col CHAR(10) CHARACTER SET latin2);
```

Server/client conversion is controlled by `character_set_client` and `character_set_connection`.

## Conversion notes

- Granularity differs: Oracle is instance-level (11g/12cR1) or database-level (12cR2); MySQL goes down to the **column** level.
- `VARCHAR2`/`NVARCHAR2` map to MySQL `CHAR`/`VARCHAR`; both UTF8 and UTF16 are expressed via `CHAR`/`VARCHAR` in MySQL rather than dedicated national types.
- **`NCHAR`/`NVARCHAR` in MySQL mean `utf8mb3`** (verified on 3.13 and 8.4: `NCHAR(10)` columns are `utf8mb3_general_ci` and reject a 4-byte character such as an emoji with error 1366). Map Oracle `NCHAR`/`NVARCHAR2` to `CHAR`/`VARCHAR` in `utf8mb4` (toolkit datatype map), never to MySQL `NCHAR`/`NVARCHAR`. `utf8mb3` and the `utf8` alias are deprecated.
- **Collation semantics:** the default `utf8mb4_0900_ai_ci` is accent- and case-insensitive (`'é' = 'e'` → 1, verified) and NO PAD. Oracle's default binary comparison is case- and accent-sensitive: use `utf8mb4_0900_as_cs` (or `utf8mb4_bin`) for columns where Oracle semantics must hold, and check unique keys — values that differ only in case or accents collide under `_ai_ci`.
- Size: `utf8mb4` uses up to 4 bytes per character. InnoDB index key prefixes are limited to 3072 bytes, so an indexed `VARCHAR(1000)` in `utf8mb4` is too long for a full index.
- `ucs2`/`utf16`/`utf32` cannot be used as client character sets; keep `character_set_client`/`connection`/`results` at `utf8mb4` (the default, verified).
- MySQL can have a different collation per database within the same instance — useful when consolidating multiple Oracle databases.

| Feature | Oracle | Aurora MySQL |
|---|---|---|
| View DB character set | `SELECT * FROM NLS_DATABASE_PARAMETERS;` | `SELECT SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME FROM INFORMATION_SCHEMA.SCHEMATA;` |
| Modify DB character set | Full export/import; DMU for Unicode | `ALTER DATABASE … CHARACTER SET utf8mb4` (default only) + `ALTER TABLE … CONVERT TO CHARACTER SET` per table |
| Granularity | Instance (11g/12cR1), Database (12cR2) | Column |
| UTF8 | `VARCHAR2` (AL32UTF8) | `CHAR`, `VARCHAR` in `utf8mb4` |
| UTF16 | `NVARCHAR2` (AL16UTF16) | `CHAR`, `VARCHAR` in `utf8mb4` |
| `NCHAR`/`NVARCHAR` | Supported | Exist, but mean `utf8mb3` — do not use |
