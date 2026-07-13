# Oracle SQL Result Cache and MySQL Query Cache

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.cache.html

**Conversion category:** Manual (three-star feature compatibility; no automation) — similar functionality but the MySQL Query Cache is deprecated/off-roadmap and should not be used.
**SCT automation:** No automation.

## Oracle

The SQL Result Cache reduces I/O by skipping the fetch step and retrieving rows from the buffer cache. Results are stored in the SGA and reused across sessions for identical statements. Most useful in data warehouses (scan many rows, return few). Related caching categories: global temporary tables, materialized views, PL/SQL collections, the `WHEN` clause.

The `RESULT_CACHE_MODE` parameter:
- `MANUAL` — cache only when a query uses the `RESULT_CACHE` hint.
- `FORCE` — cache all results unless a query uses `NO_RESULT_CACHE`.

In RAC, each instance has a private result cache (not shared). Not compatible with scalar subquery caching.

```sql
-- cache when RESULT_CACHE_MODE = MANUAL
SELECT /*+ RESULT_CACHE */ count(*) FROM bigdata_smallres_tbl;

-- skip cache when RESULT_CACHE_MODE = FORCE
SELECT /*+ NO_RESULT_CACHE */ count(*) FROM bigdata_smallres_tbl;
```

## MySQL

The MySQL Query Cache works similarly (skips the fetch step, retrieves from buffer cache, shared across sessions) but is **deprecated as of MySQL 5.7.20 and removed in MySQL 8.0**. The MySQL roadmap recommends **not** using it.

```sql
-- use the query cache
SELECT SQL_CACHE count(*) FROM bigdata_smallres_tbl;

-- bypass the query cache
SELECT SQL_NO_CACHE count(*) FROM bigdata_smallres_tbl;
```

## Conversion notes

- Do not migrate Oracle Result Cache usage to the MySQL Query Cache — it is deprecated/removed and off the roadmap.
- Remove `/*+ RESULT_CACHE */` and `/*+ NO_RESULT_CACHE */` hints; the `SQL_CACHE`/`SQL_NO_CACHE` keywords have no effect on MySQL 8 / Aurora MySQL.
- Achieve equivalent performance through other means: proper indexing, summary tables, Aurora Parallel Query, the InnoDB buffer pool, or an external cache (e.g., Amazon ElastiCache) at the application layer.
