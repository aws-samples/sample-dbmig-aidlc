# B-Tree Indexes

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.btree.html

**Conversion category:** Automatic (five-star feature compatibility, five-star automation)
**SCT automation:** N/A (fully automated).

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
