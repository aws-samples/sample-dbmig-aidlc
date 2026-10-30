# B-Tree Indexes

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.btree.html

**Conversion category:** Automatic (five-star feature compatibility, five-star automation)
**SCT automation:** N/A (fully automated).

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): deduplication, REVERSE/COMPRESS mapping, `INCLUDE`, `CONCURRENTLY`, PG 18 skip scan (verified).

## Oracle
B-tree (balanced tree) indexes are the most common index type. They are an ordered list of values divided into ranges, associating a key with a row or range of rows. Structure: **branch blocks** (for searching, including the root branch pointing to lower levels) and **leaf blocks** (storing values). Ideal for primary keys and high-cardinality columns; good for exact-match and range searches. B-tree is the **default** index type.

```sql
CREATE INDEX IDX_EVENT_ID ON SYSTEM_LOG(EVENT_ID);
```

## PostgreSQL
`CREATE INDEX` creates a B-tree by default, same as Oracle. Same characteristics; handles equality and range queries. The optimizer considers B-tree indexes especially for operators `>`, `>=`, `<`, `<=`, `=`, and also benefits `IN`, `BETWEEN`, `IS NULL`, `IS NOT NULL`.

```sql
CREATE INDEX IDX_EVENT_ID ON SYSTEM_LOG(EVENT_ID);
-- or explicitly:
CREATE INDEX IDX_EVENT_ID1 ON SYSTEM_LOG USING BTREE (EVENT_ID);
```

## Conversion notes
- Direct 1:1 conversion — identical syntax and default behavior.
- Optionally make the method explicit with `USING BTREE`.
- Oracle `COMPRESS n` (prefix compression) → drop it. PG 13+ B-tree **deduplication** is automatic.
- Oracle `REVERSE` key indexes (to spread sequence inserts) → drop `REVERSE`. Aurora has no shared-disk block contention, so a plain B-tree is fine. For equality-only lookups a `HASH` index also works.
- Oracle descending indexes (`col DESC`) and `NULLS FIRST/LAST` map directly (verified).
- Covering indexes: add non-key columns with `INCLUDE (…)` (PG 11+, verified) to get index-only scans, like Oracle indexes that contain extra columns only to avoid table access.
- Build indexes on live tables with `CREATE INDEX CONCURRENTLY` (no write lock; cannot run inside a transaction block). Oracle `ONLINE` → `CONCURRENTLY`; `REBUILD ONLINE` → `REINDEX INDEX CONCURRENTLY`.
- PG 18 B-tree **skip scan** can use a multicolumn index when the leading column is not filtered (`Index Searches: n` in `EXPLAIN ANALYZE`, verified), similar to Oracle's index skip scan.
