# SecureFile LOBs and Large Objects

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.lobs.html

**Conversion category:** Assisted (Four-star feature compatibility, four-star automation)
**SCT automation:** Four-star automation. Key difference: PostgreSQL doesn't support SecureFiles; automation/compatibility refer only to LOBs.

## Oracle

Large Objects (LOB) store binary data in the database. Oracle 11g introduced **SecureFile LOBs** (more efficient storage), created with the `SECUREFILE` keyword in `CREATE TABLE`. Primary benefits:
- **Compression** — Oracle Advanced Compression analyzes SecureFile LOB data to save disk space.
- **De-Duplication** — automatically detects and removes duplicate LOB data within a column/partition.
- **Encryption** — combined with Transparent Data Encryption (TDE).

```sql
CREATE TABLE sf_tab (COL1 NUMBER, COL2_CLOB CLOB) LOB(COL2_CLOB)
  STORE AS SECUREFILE;

CREATE TABLE sf_tab (COL1 NUMBER,COL2_CLOB CLOB) LOB(COL2_CLOB)
  STORE AS SECUREFILE COMPRESS_LOB(COMPRESS HIGH);
```

## PostgreSQL

PostgreSQL does **not** support the advanced storage/security/encryption options of SecureFile LOBs. It supports regular Large Object data types with stream-style access. Compression is handled internally by **TOAST** (The Oversized-Attribute Storage Technique), though not designed specifically for LOB columns.

Large object data types:
- **BYTEA** — stores a LOB within the table, limited to **1 GB**; octal storage supporting non-printable characters; HEX input/output format. Can store URL references to Amazon S3 objects (e.g. picture URLs).
- **TEXT** — strings of unlimited length; behaves as text when no `(n)` is specified for varchar.

For data encryption (not only LOB columns), consider **AWS Key Management Service (KMS)**.

## Conversion notes
- **SecureFiles are not supported** in PostgreSQL — only plain LOBs convert (automation/compatibility apply to LOBs only).
- Map Oracle `CLOB`/`BLOB` to PostgreSQL `TEXT` / `BYTEA` (BYTEA limited to 1 GB).
- No native LOB compression/de-dup/encryption; rely on TOAST for storage and KMS for encryption.
- Consider storing large binaries in S3 and keeping only URL references in BYTEA/TEXT.
