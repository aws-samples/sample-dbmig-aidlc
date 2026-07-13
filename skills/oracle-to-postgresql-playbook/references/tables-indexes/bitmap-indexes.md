# Bitmap Indexes

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.bitmap.html

**Conversion category:** Manual (two-star feature compatibility)
**SCT automation:** No automation. Indexes action code index. PostgreSQL doesn't support BITMAP indexes; consider BRIN in some cases.

## Oracle
Bitmap indexes are task-specific, best for OLAP / read-mostly workloads and **low-cardinality** columns (few distinct values). Unlike a B-tree (where an entry points to a row), a bitmap index stores a bitmap per index key. They perform poorly under heavy DML/OLTP.

```sql
CREATE BITMAP INDEX IDX_BITMAP_EMP_GEN ON EMPLOYEES(GENDER);
```

## PostgreSQL
Amazon Aurora PostgreSQL currently provides **no directly comparable** alternative for Oracle bitmap indexes.

## Conversion notes
- No native bitmap index in PostgreSQL/Aurora.
- For low-cardinality, large, naturally-ordered columns, a **BRIN** (Block Range Index) may serve in some cases.
- Note: PostgreSQL can build in-memory "bitmap heap scans" at query time by combining B-tree indexes, but this is a runtime execution strategy, not a persistent bitmap index object.
