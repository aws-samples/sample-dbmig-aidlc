# Composite (Multicolumn) Indexes

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.composite.html

**Conversion category:** Automatic (five-star feature compatibility, five-star automation)
**SCT automation:** Indexes action code index. No key differences.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PG 18 skip scan (verified), `INCLUDE`, `bloom`, verified key limit.

## Oracle
A multi-column / concatenated / composite index is built on multiple columns to speed `SELECT`s filtering on all or some of those columns. Place the most restrictive (most prevalent) columns first, since column order is crucial — leading columns are accessed first.

```sql
CREATE INDEX IDX_EMP_COMPI ON
  EMPLOYEES (FIRST_NAME, EMAIL, PHONE_NUMBER);

DROP INDEX IDX_EMP_COMPI;
```

## PostgreSQL
PostgreSQL multi-column indexes are equivalent to Oracle composite indexes, using the **same syntax**. Only **B-tree, GiST, GIN, and BRIN** support multi-column indexes. Up to **32 columns** per index.

```sql
CREATE INDEX IDX_EMP_COMPI
  ON EMPLOYEES (FIRST_NAME, EMAIL, PHONE_NUMBER);

DROP INDEX IDX_EMP_COMPI;
```

## Conversion notes
- Direct 1:1 conversion — identical `CREATE INDEX`/`DROP INDEX` syntax.
- Same column-order guidance applies (leading columns matter for index usability).
- Multi-column support limited to B-tree, GiST, GIN, BRIN (and the `bloom` extension); max 32 key columns (`max_index_keys = 32`, verified).
- PG 18 **skip scan**: a B-tree on `(a, b)` can now serve `WHERE b = …` when `a` has few distinct values (verified on 18.6). Before PG 18 such queries needed a separate index on `b`, so after migration check for redundant single-column indexes that Oracle's skip scan made unnecessary.
- Use `INCLUDE (cols)` for columns that are only selected, not filtered, so they don't widen the key.
