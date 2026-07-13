# Indexes

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook — Indexes
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.indexes.html

**Conversion category:** Assisted (Three-star; PostgreSQL has no CLUSTERED INDEX, a few missing options)
**SCT automation:** Three-star (medium automation); SCT action code → Indexes

## SQL Server
Indexes are B-tree structures optimizing data access; created automatically for PK and
UNIQUE constraints. Up to 250 indexes per table (999 non-clustered). Two main types:

- **Clustered index**: the table data itself, physically sorted by the key (one per table;
  a table with one is "clustered", without is a "heap"). Created by default for a PK unless
  declared `NONCLUSTERED`.
  ```sql
  CREATE CLUSTERED INDEX IDX1 ON MyTable(Col2);
  ```
- **Non-clustered index**: a separate B-tree whose leaves point to table rows (RID for heaps,
  clustering key for clustered tables). Up to 999 per table.
  ```sql
  CREATE UNIQUE NONCLUSTERED INDEX IDX1 ON MyTable(Col2);
  ```
- **Filtered indexes** (subset via `WHERE`), **covering indexes** (`INCLUDE (cols)`), and
  **indexes on persisted computed columns**.
  ```sql
  CREATE NONCLUSTERED INDEX IDX1 ON MyTable(Col2) WHERE Col2 IS NOT NULL;
  CREATE NONCLUSTERED INDEX IDX1 ON MyTable(Col2) INCLUDE (Col3);
  ```

## PostgreSQL
B-tree by default, similar to SQL Server, but different terminology/options. **No CLUSTERED
INDEX**; offers index prefix and BLOB indexing that SQL Server lacks.

- **No clustered (index-organized) table.** Closest is the one-time `CLUSTER table USING
  index;` which physically reorders rows by an existing index (not maintained automatically).
- **B-tree**: `CREATE INDEX idx ON t(col);` or `... USING BTREE (col)`. Parallel B-tree
  scans (PG10+). Monitor progress via `pg_stat_progress_create_index` (PG12+).
- **Multicolumn** (up to 32 cols): `CREATE INDEX idx ON emp(first_name, email, phone);`
- **Expression indexes**: `CREATE INDEX evnt_by_day ON system_events(EXTRACT(DAY FROM event_time));`
- **Partial indexes** (filtered equivalent): `CREATE INDEX idx ON t(event_time) WHERE event_code LIKE '01-A%';`
- **Covering**: `INCLUDE` is supported (PG11+); also `GiST`, `GIN`, `BRIN` index types.
- **BRIN** is a partial alternative to bitmap indexes for large analytic tables.

## Conversion notes
| Feature | SQL Server | Aurora PostgreSQL |
|---|---|---|
| Clustered index | Yes (table = index) | No — use `CLUSTER` (one-time reorder) |
| Non-clustered | Yes | Yes |
| Max non-clustered | 999 | effectively unbounded |
| Max columns/index | 32 | 32 |
| Filtered index | Yes | Yes (partial index) |
| Covering (`INCLUDE`) | Yes | Yes (PG11+) |
| Index prefix / BLOB index | No | Yes |

- Drop `CLUSTERED`/`NONCLUSTERED` keywords; a SQL Server clustered PK becomes a normal PG PK
  (B-tree). If physical ordering matters, document a `CLUSTER` maintenance step.
- Filtered index `WHERE` → partial index `WHERE` (mostly direct).
- Computed-column indexes → expression indexes (drop the persisted computed column, index the
  expression directly) or keep a generated column + index.
- Covering `INCLUDE` carries over (PG11+).
- No bitmap index — consider BRIN for large analytic tables; PG combines B-tree indexes via
  bitmap heap scans at query time automatically.
