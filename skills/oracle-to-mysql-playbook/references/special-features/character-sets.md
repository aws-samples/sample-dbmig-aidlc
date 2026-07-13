# Oracle and MySQL Character Sets

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.charset.html

**Conversion category:** Automatic (four-star feature compatibility; four-star automation)
**SCT automation:** N/A — handled automatically; main difference is syntax and that MySQL allows different collations per database in the same instance.

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

MySQL supports many single-byte and multi-byte character sets. The default is set when initializing the cluster with `initdb`; each database can define its own character set at creation. Query available sets with the `INFORMATION_SCHEMA.CHARACTER_SETS` table or `SHOW CHARACTER SET`; query collations with `INFORMATION_SCHEMA.COLLATIONS` or `SHOW COLLATION`.

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
ALTER DATABASE test01 CHARACTER SET = ucs2 COLLATE = ucs2_general_ci;
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
- `NCHAR`/`NVARCHAR` data types exist in both.
- MySQL can have a different collation per database within the same instance — useful when consolidating multiple Oracle databases.

| Feature | Oracle | Aurora MySQL |
|---|---|---|
| View DB character set | `SELECT * FROM NLS_DATABASE_PARAMETERS;` | `SELECT SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME FROM INFORMATION_SCHEMA.SCHEMATA;` |
| Modify DB character set | Full export/import; DMU for Unicode | `ALTER DATABASE test01 CHARACTER SET = ucs2 COLLATE = ucs2_general_ci;` |
| Granularity | Instance (11g/12cR1), Database (12cR2) | Column |
| UTF8 | `VARCHAR2`, `NVARCHAR` | `CHAR`, `VARCHAR` |
| UTF16 | `NVARCHAR2` | `CHAR`, `VARCHAR` |
| `NCHAR`/`NVARCHAR` | Supported | Supported |
