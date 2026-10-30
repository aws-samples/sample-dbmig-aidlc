# Partitioned Indexes (Local and Global)

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.partitioned.html

**Conversion category:** Manual (four-star feature compatibility, no automation)
**SCT automation:** No automation. Indexes action code index.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): declarative partitioning first, `CREATE INDEX ON ONLY` + `CONCURRENTLY` + `ATTACH PARTITION` (verified), global-index consequences.

## Oracle
Each index on a partitioned table is either **local** or **global**:
- **Local partitioned index** — one-to-one with table partitions (one index partition per table partition). Created with the `LOCAL` clause. Each index partition is independent, so maintenance is easier and automatic when table partitions are created/dropped.
- **Global partitioned index** — keys from multiple table partitions in a single index partition. Created with the `GLOBAL` clause; can be partitioned or non-partitioned (default). Restrictions apply: e.g. dropping a table partition makes the global index **unusable** until rebuilt.

```sql
-- Local index
CREATE INDEX IDX_SYS_LOGS_LOC ON SYSTEM_LOGS (EVENT_DATE)
  LOCAL
    (PARTITION EVENT_DATE_1,
    PARTITION EVENT_DATE_2,
    PARTITION EVENT_DATE_3);

-- Global index
CREATE INDEX IDX_SYS_LOGS_GLOB ON SYSTEM_LOGS (EVENT_DATE)
  GLOBAL PARTITION BY RANGE (EVENT_DATE) (
    PARTITION EVENT_DATE_1 VALUES LESS THAN (TO_DATE('01/01/2015','DD/MM/YYYY')),
    PARTITION EVENT_DATE_2 VALUES LESS THAN (TO_DATE('01/01/2016','DD/MM/YYYY')),
    PARTITION EVENT_DATE_3 VALUES LESS THAN (TO_DATE('01/01/2017','DD/MM/YYYY')),
    PARTITION EVENT_DATE_4 VALUES LESS THAN (MAXVALUE));
```

## PostgreSQL
PostgreSQL partitioning differs and has **no direct equivalent** to Oracle global indexes. Use **declarative partitioning** (inheritance-based partitioning is legacy; the inheritance example below is kept only for reading old code). With declarative partitioning, a **global index is still not supported**; creating an index on a partitioned table creates an index on each partition with a parent index referring to all sub-indexes — but no true global index.

- Indexes on child tables behave like Oracle **local** indexes (portable per-partition indexes).
- Creating an index on the parent table (analogous to an Oracle global index) has **no effect** under inheritance.
- Concurrent index builds on partitioned tables aren't supported; you can build each partition's index `CONCURRENTLY` individually, then create the partitioned index **non-concurrently** (a metadata-only operation) to minimize write lockout.
- `CREATE INDEX` on a partitioned table `RECURSE`s (default) to all partitions; if an equivalent index already exists on a partition it is attached to the parent index, otherwise a new one is created and attached automatically.

```sql
-- Parent table
CREATE TABLE SYSTEM_LOGS
  (EVENT_NO NUMERIC NOT NULL,
  EVENT_DATE DATE NOT NULL,
  EVENT_STR VARCHAR(500),
  ERROR_CODE VARCHAR(10));

-- Child tables (partitions) with check constraints (inheritance)
CREATE TABLE SYSTEM_LOGS_WARNING (
  CHECK (ERROR_CODE IN('err1', 'err2', 'err3')))
  INHERITS (SYSTEM_LOGS);

CREATE TABLE SYSTEM_LOGS_CRITICAL (
  CHECK (ERROR_CODE IN('err4', 'err5', 'err6')))
  INHERITS (SYSTEM_LOGS);

-- Local-like indexes on each child table
CREATE INDEX IDX_SYSTEM_LOGS_WARNING ON SYSTEM_LOGS_WARNING(ERROR_CODE);
CREATE INDEX IDX_SYSTEM_LOGS_CRITICAL ON SYSTEM_LOGS_CRITICAL(ERROR_CODE);
```

## Conversion notes
- Map Oracle **local** indexes to an index on the **partitioned parent** (declarative partitioning). It creates and maintains one index per partition, including partitions created later — the closest behavioral match.
- Build without long write locks (verified on 18.6):
  ```sql
  CREATE INDEX pix_idx ON ONLY pix (id);                 -- parent index, initially invalid
  CREATE INDEX CONCURRENTLY pix_1_idx ON pix_1 (id);     -- per partition, online
  ALTER INDEX pix_idx ATTACH PARTITION pix_1_idx;        -- parent becomes valid when all are attached
  ```
- Oracle **global** partitioned indexes have **no equivalent**; redesign queries/maintenance accordingly. A global *unique* index that excludes the partition key cannot be reproduced (see `../physical-storage/table-partitioning-and-inheritance.md`). Non-unique global indexes become local indexes, and queries without the partition key scan every partition's index.
- To reduce write lockout on large partitioned tables: build each partition's index `CONCURRENTLY`, then attach via a non-concurrent partitioned `CREATE INDEX` (metadata-only).
- Prefer declarative partitioning on modern PostgreSQL/Aurora; under it, a `CREATE INDEX` on the partitioned table cascades to all partitions automatically.
