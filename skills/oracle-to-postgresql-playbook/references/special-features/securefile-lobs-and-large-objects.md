# SecureFile LOBs and Large Objects

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.lobs.html

**Conversion category:** Assisted (Four-star feature compatibility, four-star automation)
**SCT automation:** Four-star automation. Key difference: PostgreSQL doesn't support SecureFiles; automation/compatibility refer only to LOBs.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): 1 GB limit also applies to `text`, per-column `lz4` TOAST compression (verified), large objects for >1 GB, DMS LOB modes, `DBMS_LOB` function mapping.

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

PostgreSQL does **not** support the advanced storage/security/encryption options of SecureFile LOBs. It supports regular Large Object data types with stream-style access. Compression is handled internally by **TOAST** (The Oversized-Attribute Storage Technique) for values over about 2 kB. Since PG 14 the method is selectable per column, `pglz` (Aurora default) or **`lz4`** (faster, verified on 18.6):
```sql
CREATE TABLE docs (id bigint, body text COMPRESSION lz4, img bytea);
SELECT pg_column_compression(body), pg_column_size(body) FROM docs;   -- 100,000-char text stored in 411 bytes (verified)
-- or cluster-wide: default_toast_compression = lz4 (parameter group)
```

Large object data types:
- **BYTEA** — stores a LOB within the table, limited to **1 GB**; octal storage supporting non-printable characters; HEX input/output format. Can store URL references to Amazon S3 objects (e.g. picture URLs).
- **TEXT** — variable-length strings up to **1 GB** per value (same limit as `bytea`); `varchar` without `(n)` behaves the same.
- **Large objects** (`oid` reference + `pg_largeobject`, `lo_*` functions, `lo` extension available on Aurora 18) — up to 4 TB per object with streaming read/write. Needed only for values over 1 GB or true streaming. They are not deleted with the row (use the `lo_manage` trigger from the `lo` extension), and logical replication and AWS DMS do not replicate them.

For data encryption (not only LOB columns), consider **AWS Key Management Service (KMS)**.

## Conversion notes
- **SecureFiles are not supported** in PostgreSQL — only plain LOBs convert (automation/compatibility apply to LOBs only).
- Map Oracle `CLOB`/`NCLOB` → `text`, `BLOB` → `bytea` (both limited to 1 GB per value). Check `MAX(DBMS_LOB.GETLENGTH(col))` at the source during assessment; values over 1 GB need `oid` large objects or S3.
- `COMPRESS` SecureFiles → `COMPRESSION lz4` on the column. There is no de-duplication; storage encryption (KMS) covers encryption.
- AWS DMS LOB settings (limited vs full LOB mode, `LobMaxSize`) decide whether large values arrive intact. Validate the maximum LOB length after the load.
- `DBMS_LOB` calls: `GETLENGTH` → `length()` / `octet_length()`, `SUBSTR` → `substr()` / `substring(bytea …)`, `INSTR` → `strpos()` / `position()`, `APPEND` → `||`. orafce has no `DBMS_LOB` package.
- Consider storing large binaries in S3 and keeping only URL references in BYTEA/TEXT.
