# Indexes Summary

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.indexes.html

**Conversion category:** Assisted (high syntax similarity; some Oracle index types unsupported)
**SCT automation:** N/A (overview page).

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): corrected Hash (crash-safe) and SP-GiST (core) claims, HypoPG available, parallel builds and deduplication supported, local indexes map to parent indexes, tablespaces have no effect on Aurora.

## Oracle
Oracle supports many index types/features: B-Tree, index-organized tables, reverse key, descending, B-tree cluster, unique/non-unique, function-based, application-domain, bitmap/bitmap-join, composite, invisible, local/global, partial indexes for partitioned tables (12c), index parallel operations, and index (key/advanced) compression. Standard DDL: `CREATE INDEX`, `DROP INDEX`, `ALTER INDEX ... RENAME/REBUILD/TABLESPACE`.

```sql
CREATE UNIQUE INDEX IDX_EMP_ID ON EMPLOYEES (EMPLOYEE_ID DESC);
DROP INDEX IDX_EMP_ID;
ALTER INDEX IDX_EMP_ID RENAME TO IDX_EMP_ID_OLD;
ALTER INDEX IDX_EMP_ID REBUILD TABLESPACE USER_IDX;
ALTER INDEX IDX_EMP_ID REBUILD;
ALTER INDEX IDX_EMP_ID REBUILD ONLINE;
```

## PostgreSQL
Built-in index types (Aurora-supported):
- **B-Tree** — default; equality and range; all data types; can retrieve NULLs; sorted ascending by default.
- **Hash** — equality only. WAL-logged and crash-safe since PG 10 (the old "not transaction-safe" warning no longer applies); smaller than B-tree for long keys.
- **GIN** (Generalized Inverted Index) — maps many values to one row; good for full-text search and array values.
- **GiST** (Generalized Search Tree) — index infrastructure for complex operations beyond equality/range; geometric types and full-text search.
- **BRIN** (Block Range Index) — stores min/max summary per range of physical table blocks; rules out records to cut runtime.
- **SP-GiST** (space-partitioned GiST) — built into core PostgreSQL (verified on 18.6), for tries, quad-trees, ranges, and text prefix search. (The original playbook said it required an unavailable extension; that is wrong.)
- Extension index types available on Aurora 18: `bloom`, `btree_gin`, `btree_gist`, `pg_trgm` (GIN/GiST trigram for `LIKE '%x%'`), `pg_bigm`, PostGIS, and pgvector (`hnsw`, `ivfflat`).

PostgreSQL 12+ can monitor `CREATE INDEX`/`REINDEX` via `pg_stat_progress_create_index`.

**CREATE INDEX synopsis:**
```sql
CREATE [ UNIQUE ] INDEX [ CONCURRENTLY ] [ [ IF NOT EXISTS ] name ]
ON table_name [ USING method ]
( { column_name | ( expression ) } [ COLLATE collation ] [ opclass ] [ ASC | DESC ]
  [ NULLS { FIRST | LAST } ] [, ...] )
[ WITH ( storage_parameter = value [, ... ] ) ]
[ TABLESPACE tablespace_name ]
[ WHERE predicate ]
```
Default is a B-Tree index.

```sql
CREATE UNIQUE INDEX IDX_EMP_ID ON EMPLOYEES (EMPLOYEE_ID DESC);
DROP INDEX IDX_EMP_ID;
ALTER INDEX IDX_EMP_ID RENAME TO IDX_EMP_ID_OLD;
CREATE TABLESPACE PGIDX LOCATION '/data/indexes';
ALTER INDEX IDX_EMP_ID SET TABLESPACE PGIDX;
REINDEX INDEX IDX_EMP_ID;                                  -- = REBUILD
-- Online rebuild equivalent:
CREATE INDEX CONCURRENTLY IDX_EMP_ID1 ON EMPLOYEES(EMPLOYEE_ID);
DROP INDEX CONCURRENTLY IDX_EMP_ID;
```

### Mapping summary
| Oracle index type/feature | PostgreSQL compatibility | PostgreSQL equivalent |
|---|---|---|
| B-Tree | Supported | B-Tree |
| Index-organized tables | Supported | PostgreSQL CLUSTER |
| Reverse key indexes | Not supported | Drop `REVERSE` (plain B-tree); Aurora has no shared-disk block contention |
| Descending indexes | Supported | ASC (default) / DESC |
| B-tree cluster indexes | Not supported | N/A |
| Unique / non-unique | Supported | Identical syntax; `UNIQUE NULLS NOT DISTINCT` (PG 15+) for Oracle-like treatment of all-NULL keys |
| Function-based indexes | Supported | Expression indexes (expressions must be `IMMUTABLE`) |
| Application domain indexes (Oracle Text, Spatial) | Partial | Full-text: GIN on `tsvector`, `pg_trgm`; spatial: PostGIS GiST |
| BITMAP / bitmap-join | Not supported | B-tree (dedup), partial, `bloom`, BRIN; bitmap heap scans at runtime |
| Composite indexes | Supported | Multicolumn indexes; PG 18 skip scan |
| Invisible indexes | Not supported | HypoPG hypothetical indexes **are available on Aurora 18** (verified) for the "what-if" use case |
| Local indexes | Supported | Index on the partitioned parent (one index per partition) |
| Global indexes | Not supported | N/A — unique keys must include the partition key |
| Partial indexes for partitioned tables (12c `INDEXING OFF`) | Partial | Create the index only on the partitions that need it, or use a partial index `WHERE` on the key range |
| CREATE INDEX / DROP INDEX | Supported | High syntax similarity |
| ALTER INDEX (general) | Supported | N/A |
| ALTER INDEX REBUILD | Supported | REINDEX |
| ALTER INDEX REBUILD ONLINE | Limited support | CONCURRENTLY |
| Index metadata | USER_INDEXES | PG_INDEXES |
| Index tablespace allocation | Supported | SET TABLESPACE |
| Index parallel operations | Supported | Parallel B-tree build (PG 11+) and BRIN build (PG 17+), controlled by `max_parallel_maintenance_workers` (default 2 on Aurora 18) |
| Index compression | Partial | B-tree deduplication (PG 13+, automatic) |

## Conversion notes
- Most CREATE/DROP/ALTER index DDL is syntactically similar; biggest gaps are reverse-key, bitmap, application-domain, invisible, local/global, and partitioned partial indexes.
- `ALTER INDEX ... REBUILD` → `REINDEX`; `REBUILD ONLINE` → `CREATE INDEX CONCURRENTLY` (+ `DROP INDEX CONCURRENTLY`).
- Function-based indexes → expression indexes; composite → multicolumn; IOT → CLUSTER.
- Oracle index key compression → automatic B-tree deduplication. Oracle `PARALLEL` index builds → raise `max_parallel_maintenance_workers` for the session.
- `CREATE TABLESPACE … LOCATION` and `SET TABLESPACE` are accepted on Aurora but have no storage effect (one cluster volume). Omit index tablespaces in converted DDL.
