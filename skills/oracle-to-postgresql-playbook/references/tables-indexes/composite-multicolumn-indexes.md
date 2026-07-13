# Composite (Multicolumn) Indexes

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.composite.html

**Conversion category:** Automatic (five-star feature compatibility, five-star automation)
**SCT automation:** Indexes action code index. No key differences.

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
- Multi-column support limited to B-tree, GiST, GIN, BRIN; max 32 columns.
