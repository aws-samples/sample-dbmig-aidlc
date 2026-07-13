# Oracle SecureFile LOBs and MySQL Large Objects

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.lobs.html

**Conversion category:** Assisted (four-star feature compatibility; four-star automation) — MySQL doesn't support SecureFiles; compatibility/automation refer to plain LOBs only.
**SCT automation:** N/A

## Oracle

LOBs store binary data in the database. Oracle 11g introduced SecureFile LOBs (created with the `SECUREFILE` keyword) for more efficient storage. Benefits: compression (Oracle Advanced Compression), de-duplication (removes duplicate LOB data), and encryption (with TDE).

```sql
CREATE TABLE sf_tab (COL1 NUMBER, COL2_CLOB CLOB) LOB(COL2_CLOB)
  STORE AS SECUREFILE;

-- with LOB compression
CREATE TABLE sf_tab (COL1 NUMBER, COL2_CLOB CLOB) LOB(COL2_CLOB)
  STORE AS SECUREFILE COMPRESS_LOB(COMPRESS HIGH);
```

## MySQL

MySQL does not support SecureFile advanced storage/security/encryption options, but supports regular LOB types with stream-style access.

- **BLOB types** (binary, byte strings; sorted by byte numeric value): `TINYBLOB`, `BLOB`, `MEDIUMBLOB`, `LONGBLOB`.
- **TEXT types** (non-binary character strings; sorted/compared by character set collation): `TINYTEXT`, `TEXT`, `MEDIUMTEXT`, `LONGTEXT`.

These differ only in maximum length. For `TEXT` columns, index entries are space-padded; a unique index raises duplicate-key errors for values differing only in trailing spaces (e.g., 'b' vs 'b ').

Constraints:
- Only the first `max_sort_length` bytes (default 1024) are used when sorting/grouping; adjustable at startup/runtime.
- BLOB/TEXT in a query that uses a temporary table forces an on-disk table (MEMORY engine doesn't support these types) — a performance penalty; include them only when essential.
- The largest transmittable value is bounded by `max_allowed_packet` (must be set on both server and client).

Create a table with a BLOB column and a prefix index:

```sql
CREATE TABLE test (blob_col BLOB, INDEX(blob_col(10)));
```

## Conversion notes

- Map Oracle `CLOB` → MySQL `TEXT` family; Oracle `BLOB`/SecureFile binary → MySQL `BLOB` family, sized appropriately (`LONGBLOB`/`LONGTEXT` for the largest).
- SecureFile compression, de-duplication, and TDE encryption have **no equivalent** — rely on Aurora storage-level encryption (KMS) and handle compression/de-dup at the application layer if needed.
- BLOB/TEXT columns can only be indexed with a **prefix length** (e.g., `INDEX(blob_col(10))`).
- Tune `max_allowed_packet` and be aware of `max_sort_length` and temp-table-to-disk behavior for large values.
