# Indexes Summary

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.indexes.html

**Conversion category:** Assisted (high syntax similarity; some Oracle index types unsupported)
**SCT automation:** N/A (overview page).

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
- **Hash** — equality only; rarely used (not transaction-safe, manual rebuild on failure).
- **GIN** (Generalized Inverted Index) — maps many values to one row; good for full-text search and array values.
- **GiST** (Generalized Search Tree) — index infrastructure for complex operations beyond equality/range; geometric types and full-text search.
- **BRIN** (Block Range Index) — stores min/max summary per range of physical table blocks; rules out records to cut runtime.

SP-GiST and similar require a loadable extension not available in Aurora PostgreSQL. PostgreSQL 12+ can monitor `CREATE INDEX`/`REINDEX` via `pg_stat_progress_create_index`.

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
| Reverse key indexes | Not supported | N/A |
| Descending indexes | Supported | ASC (default) / DESC |
| B-tree cluster indexes | Not supported | N/A |
| Unique / non-unique | Supported | Identical syntax |
| Function-based indexes | Supported | Expression indexes |
| Application domain indexes | Not supported | N/A |
| BITMAP / bitmap-join | Not supported | Consider BRIN |
| Composite indexes | Supported | Multicolumn indexes |
| Invisible indexes | Not supported | hypopg extension not supported |
| Local and global indexes | Not supported | N/A |
| Partial indexes for partitioned tables (12c) | Not supported | N/A |
| CREATE INDEX / DROP INDEX | Supported | High syntax similarity |
| ALTER INDEX (general) | Supported | N/A |
| ALTER INDEX REBUILD | Supported | REINDEX |
| ALTER INDEX REBUILD ONLINE | Limited support | CONCURRENTLY |
| Index metadata | USER_INDEXES | PG_INDEXES |
| Index tablespace allocation | Supported | SET TABLESPACE |
| Index parallel operations | Not supported | N/A |
| Index compression | No direct equivalent | N/A |

## Conversion notes
- Most CREATE/DROP/ALTER index DDL is syntactically similar; biggest gaps are reverse-key, bitmap, application-domain, invisible, local/global, and partitioned partial indexes.
- `ALTER INDEX ... REBUILD` → `REINDEX`; `REBUILD ONLINE` → `CREATE INDEX CONCURRENTLY` (+ `DROP INDEX CONCURRENTLY`).
- Function-based indexes → expression indexes; composite → multicolumn; IOT → CLUSTER.
- No Oracle-style index key compression or parallel index builds in Aurora PostgreSQL.
