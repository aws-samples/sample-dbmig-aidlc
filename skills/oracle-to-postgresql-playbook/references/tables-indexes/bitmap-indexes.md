# Bitmap Indexes

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.bitmap.html

**Conversion category:** Manual (two-star feature compatibility)
**SCT automation:** No automation. Indexes action code index. PostgreSQL doesn't support BITMAP indexes; consider BRIN in some cases.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): B-tree deduplication, PG 18 skip scan, partial and `bloom` indexes as replacements (verified); default conversion rule.

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
- Note: PostgreSQL can build in-memory "bitmap heap scans" at query time by combining B-tree indexes, but this is a runtime execution strategy, not a persistent bitmap index object. This is what replaces most Oracle bitmap-index **combinations** (`WHERE gender = 'F' AND region = 'EU'` → BitmapAnd of two B-trees).
- Better options on Aurora PostgreSQL 18 (all verified):
  - A plain **B-tree**: since PG 13, B-tree **deduplication** stores repeated keys compactly, so a B-tree on a low-cardinality column is far smaller than before.
  - A **multicolumn B-tree** with the low-cardinality column first. The PG 18 **skip scan** can use it even when the query filters only on the second column.
  - A **partial index** when queries target one rare value: `CREATE INDEX ON employees (hire_date) WHERE status = 'TERMINATED';`
  - The **`bloom`** extension for equality filters on arbitrary combinations of many columns (`CREATE INDEX … USING bloom (c1, c2, c3)`).
  - **BRIN** for large, naturally ordered columns (dates, sequence-like keys).
- Default conversion: Oracle `CREATE BITMAP INDEX` → plain `CREATE INDEX` (B-tree), with a note in the conversion log. Revisit after performance testing.
