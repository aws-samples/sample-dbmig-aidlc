# Oracle SecureFile LOBs and MySQL Large Objects

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.lobs.html

**Conversion category:** Assisted (four-star feature compatibility; four-star automation) — MySQL doesn't support SecureFiles; compatibility/automation refer to plain LOBs only.
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected the trailing-space/unique-index claim for NO PAD collations (verified), prefix-index error 1170, size and packet limits, DBMS_LOB mapping, S3 for large files.

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

These differ only in maximum length (`TEXT` 64 KB, `MEDIUMTEXT` 16 MB, `LONGTEXT` 4 GB; sizes are in bytes, so `utf8mb4` text holds fewer characters). With the default **NO PAD** collation `utf8mb4_0900_ai_ci`, trailing spaces are significant: a unique prefix index on a `TEXT` column accepts both `'b'` and `'b '` (verified on 3.13 and 8.4). The original playbook described PAD SPACE collations, where they collide.

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
- BLOB/TEXT columns can only be indexed with a **prefix length** (e.g., `INDEX(blob_col(10))`; without it error 1170, verified), or through a generated column / functional index on a hash (`INDEX ((MD5(col)))`) for equality lookups.
- `max_allowed_packet` is 64 MB by default on Aurora (verified) and `max_sort_length` 1024 bytes; raise `max_allowed_packet` in the parameter group for documents larger than that, and on the client too.
- Oracle `DBMS_LOB` piecewise APIs (`READ`, `WRITE`, `APPEND`, `INSTR`, `SUBSTR`) → whole-value string functions (`SUBSTRING`, `CONCAT`, `LOCATE`) or streaming in the application driver.
- Large LOBs make every update rewrite the value; store big immutable files in Amazon S3 and keep the key in the table where possible.
- Tune `max_allowed_packet` and be aware of `max_sort_length` and temp-table-to-disk behavior for large values.
