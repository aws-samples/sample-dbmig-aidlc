# Automatic Indexing

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.autoindex.html

**Conversion category:** Blocked (one-star feature compatibility)
**SCT automation:** No automation. Indexes action code index. PostgreSQL has no automatic indexing. HypoPG **is** available on Aurora PostgreSQL 18 (see below).

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): HypoPG is available on Aurora 18 (verified; the old 'not supported' claim was removed), Dexter works client-side, `last_idx_scan`, per-instance index stats.

## Oracle
Oracle 19c introduced **automatic indexing**, which automatically creates, rebuilds, and drops indexes based on workload changes. Functionality:
- A background process runs at a predefined interval, analyzes workload, and identifies table/column candidates for new indexes.
- Auto indexes are created **invisible** first, validated against SQL statements, and only made **visible** if performance improves.
- Identifies and drops under-performing or long-unused auto indexes.
- Rebuilds auto indexes marked unusable by DDL.
- Configured/reported via the `DBMS_AUTO_INDEX` package.

> Up-to-date table statistics are essential; tables with no/stale statistics aren't considered.

`DBMS_AUTO_INDEX.CONFIGURE` options: enable/disable auto indexing; specify schemas/tables eligible; retention period for unused auto indexes (default **373 days**); retention for unused non-auto indexes; tablespace and percentage for auto indexes. Reports via `REPORT_ACTIVITY` and `REPORT_LAST_ACTIVITY`.

## PostgreSQL
PostgreSQL has **no** automatic indexing feature. **HypoPG 1.4.2 is available on Aurora PostgreSQL 18** (verified on 18.6). It creates *hypothetical* indexes that only the planner sees, so you can test "would this index be used, and how much would it save?" without building anything. **Dexter** is a client-side tool that drives HypoPG with `pg_stat_statements` data, so it also works against Aurora. (The original playbook said neither was supported on Aurora; that is outdated.)

```sql
CREATE EXTENSION hypopg;
SELECT * FROM hypopg_create_index('CREATE INDEX ON orders (customer_id)');
EXPLAIN SELECT * FROM orders WHERE customer_id = 42;     -- shows the hypothetical index if chosen
SELECT hypopg_reset();
```

These extensions: identify queries → refresh stale statistics → get initial query cost and create **hypothetical** indexes on un-indexed columns → re-cost and keep hypothetical indexes that were used and significantly reduced cost.

For Aurora, an alternative is a scheduled set of diagnostic queries:

Find user tables without primary keys:
```sql
SELECT c.table_schema, c.table_name, c.table_type
FROM information_schema.tables c
WHERE c.table_schema NOT IN('information_schema', 'pg_catalog') AND c.table_type = 'BASE TABLE'
AND NOT EXISTS(SELECT i.tablename FROM pg_catalog.pg_indexes i
  WHERE i.schemaname = c.table_schema
  AND i.tablename = c.table_name AND indexdef LIKE '%UNIQUE%')
AND NOT EXISTS (SELECT cu.table_name FROM information_schema.key_column_usage cu
  WHERE cu.table_schema = c.table_schema AND cu.table_name = c.table_name)
ORDER BY c.table_schema, c.table_name;
```

Geometry tables with no index on the geometry column:
```sql
SELECT c.table_schema, c.table_name, c.column_name
FROM (SELECT * FROM information_schema.tables WHERE table_type = 'BASE TABLE') As t
INNER JOIN (SELECT * FROM information_schema.columns WHERE udt_name = 'geometry') c
  ON (t.table_name = c.table_name AND t.table_schema = c.table_schema)
  LEFT JOIN pg_catalog.pg_indexes i ON
  (i.tablename = c.table_name AND i.schemaname = c.table_schema
  AND indexdef LIKE '%' || c.column_name || '%')
WHERE i.tablename IS NULL
ORDER BY c.table_schema, c.table_name;
```

Unused indexes that can probably be dropped (PG 16+ adds `last_idx_scan`, verified):
```sql
SELECT s.relname, indexrelname, i.indisunique, idx_scan, last_idx_scan
FROM pg_catalog.pg_stat_user_indexes s, pg_index i
WHERE i.indexrelid = s.indexrelid AND idx_scan = 0 AND NOT i.indisunique;
```
Statistics are per instance: check the writer **and** every reader before dropping, because an index used only by reporting queries on a replica shows `idx_scan = 0` on the writer.

## Conversion notes
- No automatic-indexing equivalent on Aurora PostgreSQL. The Oracle safety model (create invisible → validate → make visible) maps to **HypoPG** for "validate before create" (hypothetical index, planner-only) and to **QPM** (`apg_plan_mgmt`) for keeping known-good plans while you test index changes. There is no invisible *real* index (see `invisible-indexes.md`).
- Dexter + HypoPG can recommend indexes on Aurora. Review the recommendations; do not apply them automatically.
- Build recommended indexes with `CREATE INDEX CONCURRENTLY` to avoid blocking writes.
- Do **not** auto-apply create/drop decisions from the diagnostic queries in production; use them as guidance and validate changes carefully (no harmless invisible-index validation step exists).
