# Oracle Table Compression

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.tablecompression.html

**Conversion category:** Manual (three-star feature compatibility) — similar functionality, syntax/option differences; Aurora MySQL doesn't compress partitions.
**SCT automation:** N/A

## Oracle

Table compression reduces data size, saving disk space and memory and speeding up read-heavy queries, at the cost of higher CPU during load/DML. Transparent to applications; common in OLAP but also usable in OLTP. Set at `CREATE TABLE` or via `ALTER TABLE` with the `COMPRESS` clause.

Compression clause options:
- `NOCOMPRESS` — default, no compression.
- `COMPRESS` — compress during direct-path inserts only.
- `COMPRESS FOR DIRECT_LOAD OPERATIONS` — direct-path inserts only.
- `COMPRESS FOR ALL OPERATIONS` — all operations including DML (typical for OLTP).

View compression status:

```sql
SELECT OWNER, TABLE_NAME, COMPRESSION, COMPRESS_FOR FROM dba_tables;
```

Create a compressed table:

```sql
CREATE TABLE comp_tbl
(id NUMBER NOT NULL,
 created_date DATE NOT NULL)
COMPRESS FOR ALL OPERATIONS;
```

Partitioned table with per-partition compression:

```sql
CREATE TABLE comp_part_tbl
(id NUMBER NOT NULL,
 created_date DATE NOT NULL)
PARTITION BY RANGE (created_date) (
PARTITION comp_part_tbl_q1 VALUES LESS THAN (TO_DATE('01/01/2018','DD/MM/YYYY')) COMPRESS,
PARTITION comp_part_tbl_q2 VALUES LESS THAN (TO_DATE('01/04/2018','DD/MM/YYYY')) COMPRESS FOR DIRECT_LOAD OPERATIONS,
PARTITION comp_part_tbl_q3 VALUES LESS THAN (TO_DATE('01/07/2018','DD/MM/YYYY')) COMPRESS FOR ALL OPERATIONS,
PARTITION comp_part_tbl_q4 VALUES LESS THAN (MAXVALUE) NOCOMPRESS);
```

## MySQL

Aurora MySQL does **not** support compressed tables (`ROW_FORMAT=COMPRESSED`). Expand compressed tables by setting `ROW_FORMAT` to `DEFAULT`, `COMPACT`, `DYNAMIC`, or `REDUNDANT`.

```sql
ALTER TABLE my_tbl ROW_FORMAT=DYNAMIC;
```

## Conversion notes

- Remove Oracle `COMPRESS`/`COMPRESS FOR ...` clauses; set Aurora MySQL `ROW_FORMAT` to a non-compressed format (`DEFAULT`/`COMPACT`/`DYNAMIC`/`REDUNDANT`).
- InnoDB `ROW_FORMAT=COMPRESSED` is not available on Aurora MySQL — do not rely on table-level compression for storage savings.
- Per-partition compression has no equivalent.
- Aurora's storage layer manages space differently; storage/cost optimization is handled at the Aurora storage level rather than via table compression.
