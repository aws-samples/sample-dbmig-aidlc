# Post-Cutover Monitoring — demodb.demo (Aurora PostgreSQL 17.7)

Two jobs: (1) catch a rollback trigger fast, (2) confirm the migration is genuinely correct, not
merely "up". Queries below are runnable as-is.

**Prerequisite:** `pg_stat_statements` in `shared_preload_libraries`, Performance Insights and
Enhanced Monitoring enabled (runbook 0.4).

> Status: `pg_stat_statements` has already been **verified available and installed** on
> `demodb` (`CREATE EXTENSION IF NOT EXISTS pg_stat_statements`) and query 3a below was executed
> successfully, so this section is ready to use as-is. Every query in this document was run
> against the target and confirmed working.

---

## Cadence

| Window | Attention |
|---|---|
| **T+0 → T+60 min** | Every 5–10 min, someone watching. Rollback armed. |
| **T+1 h → T+24 h** | Hourly spot checks; alarms carry the load. |
| **T+1 → T+7 days** | Daily review; close out the soak. |

---

## 1. Errors — the primary rollback signal

Application error rate vs. its pre-migration baseline is the top-line metric. Watch specifically
for these migration-specific failure modes:

| Symptom | Almost certainly means |
|---|---|
| `duplicate key value violates unique constraint "pk_*"` | An **identity sequence is behind `MAX(id)`** — runbook 2.4 was skipped or failed. Fix: `SELECT setval(pg_get_serial_sequence('demo.<t>','id'), (SELECT MAX(id) FROM demo.<t>));` |
| `relation "..." does not exist` | `search_path`/`currentSchema=demo` missing from the connection string, or the app is still using unqualified Oracle names |
| `function ... does not exist` | App still calling `PKG.PROC(...)` instead of the flattened `demo.pkg_proc(...)` |
| Unhandled `U0001` / `U0002` | App still catching `ORA-20001`/`ORA-20002` |
| Writes silently lost / not visible | App relying on the removed `COMMIT` in the 4 converted procedures — the caller must now commit |
| `P0002 query returned no rows` surfacing to users | A `SELECT INTO STRICT` path that Oracle handled via `NO_DATA_FOUND`; check the caller's exception handling |
| Search returns nothing for valid terms | Query not converted to `@@ to_tsquery(...)`, or the term is an English stopword |

Server-side error scan (CloudWatch Logs → `postgresql.log`), filter patterns:
`ERROR`, `FATAL`, `duplicate key`, `does not exist`, `deadlock detected`, `U0001`, `U0002`.

---

## 2. Correctness — prove the migration, don't just prove uptime

```sql
-- 2a. Row counts must not silently drift from the cutover baseline (199 at T+0, then growing
--     only in orders / order_items / shopping_cart_items).
SELECT 'addresses' t, count(*) FROM demo.addresses
UNION ALL SELECT 'books', count(*) FROM demo.books
UNION ALL SELECT 'books_cover', count(*) FROM demo.books_cover
UNION ALL SELECT 'customers', count(*) FROM demo.customers
UNION ALL SELECT 'listings', count(*) FROM demo.listings
UNION ALL SELECT 'orders', count(*) FROM demo.orders
UNION ALL SELECT 'order_items', count(*) FROM demo.order_items
UNION ALL SELECT 'shopping_cart_items', count(*) FROM demo.shopping_cart_items
ORDER BY 1;

-- 2b. Identity headroom — the most likely early failure mode: a sequence at or behind
--     MAX(id) means the next application insert raises a duplicate-key error.
--     This lists each identity table with its sequence's current position.
SELECT c.relname AS tbl, a.attname AS col, s.sequencename, s.last_value
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attidentity <> ''
JOIN pg_depend d ON d.refobjid = c.oid AND d.refobjsubid = a.attnum
                AND d.classid = 'pg_class'::regclass
JOIN pg_class sc ON sc.oid = d.objid AND sc.relkind = 'S'
JOIN pg_sequences s ON s.schemaname = n.nspname AND s.sequencename = sc.relname
WHERE n.nspname = 'demo'
ORDER BY 1;
-- For the authoritative pass/fail (each sequence compared against its OWN table's MAX(id)),
-- run check 3 of 04-operations/smoke-test.sql — it RAISES on any table that is behind.

-- 2c. Full-text search still works AND still uses the GIN index.
EXPLAIN SELECT id FROM demo.books
WHERE to_tsvector('english', coalesce(search_text,'')) @@ to_tsquery('english','iron');
-- MUST show "Bitmap Index Scan on books_text_idx". A Seq Scan means the index is unused.

-- 2d. The search trigger is still maintaining search_text (0 = healthy).
SELECT count(*) AS rows_with_stale_search_text
FROM demo.books
WHERE search_text IS DISTINCT FROM
      lower(title) || ' ' || lower(coalesce(author,'')) || ' ' || lower(coalesce(isbn,''));
```

Re-running the full technical smoke test at T+1 h and T+24 h is cheap and worthwhile:
`psql -h aurora-cluster.example.com -U <app_user> -d demodb -v ON_ERROR_STOP=1 -f 04-operations/smoke-test.sql`

---

## 3. Performance

```sql
-- 3a. Slowest statements by total time.
--     Reset the baseline right after cutover with:  SELECT pg_stat_statements_reset()
SELECT calls,
       round(total_exec_time::numeric, 1)  AS total_ms,
       round(mean_exec_time::numeric, 2)   AS mean_ms,
       rows,
       left(query, 120) AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

-- 3b. Sequential scans on tables that have indexes — a classic post-migration plan regression.
SELECT relname, seq_scan, seq_tup_read, idx_scan
FROM pg_stat_user_tables
WHERE schemaname = 'demo'
ORDER BY seq_scan DESC;

-- 3c. Are the indexes we migrated actually being used? Persistent idx_scan = 0 on a
--     high-traffic table means the app's query shape changed during conversion.
SELECT relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'demo'
ORDER BY idx_scan, relname;
```

**Expect some slowness in the first minutes** — caches are cold and statistics are fresh from the
bulk load. Run `ANALYZE` (runbook 5.3) before concluding there is a regression. Escalate to R7
only if a regression persists after `ANALYZE` and cache warm-up.

Tuning references: `oracle-to-postgresql-playbook/references/performance-tuning/run-plans.md`,
`.../table-statistics.md`, `.../hints-and-query-planning.md` (PostgreSQL has no optimizer hints —
fix statistics and indexes instead).

---

## 4. Connections and locks

```sql
-- 4a. Connection headroom (must stay below max_connections).
SELECT count(*) AS total,
       count(*) FILTER (WHERE state = 'active')                AS active,
       count(*) FILTER (WHERE state = 'idle in transaction')    AS idle_in_txn
FROM pg_stat_activity WHERE datname = 'demodb';
SHOW max_connections;

-- 4b. Blocking / long-running sessions.
SELECT pid, state, wait_event_type, wait_event,
       now() - xact_start AS txn_age, left(query, 100) AS query
FROM pg_stat_activity
WHERE datname = 'demodb' AND state <> 'idle'
ORDER BY xact_start;
```

`idle in transaction` climbing is a strong signal of change #3 not being applied — the app is no
longer getting an implicit `COMMIT` from the converted procedures and is holding transactions
open. Consider RDS Proxy if the pool churns
(`.../references/tools/rds-proxy.md`).

---

## 5. Vacuum, bloat and storage

```sql
-- 5a. Autovacuum health and dead-tuple accumulation.
SELECT relname, n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'demo'
ORDER BY n_dead_tup DESC;

-- 5b. Table + TOAST sizes. books_cover holds the BLOB -> bytea data in TOAST storage.
SELECT relname,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'demo' AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC;

-- 5c. Transaction-ID wraparound headroom (should be far from autovacuum_freeze_max_age).
SELECT max(age(relfrozenxid)) AS oldest_xid_age FROM pg_class WHERE relkind = 'r';
```

---

## 6. CloudWatch alarms to have in place

| Metric | Suggested threshold |
|---|---|
| `CPUUtilization` | > 80% for 10 min |
| `DatabaseConnections` | > 80% of `max_connections` |
| `FreeableMemory` | < 10% of instance memory |
| `FreeLocalStorage` | < 10% |
| `ReadLatency` / `WriteLatency` | > 2× the observed post-cutover baseline |
| `Deadlocks` | > 0 |
| `AuroraReplicaLag` (if readers exist) | > 1000 ms |
| Log filter: `ERROR`/`FATAL` count | above the app's normal baseline |

If DMS CDC is used for a production-scale rerun, also alarm on `CDCLatencySource`/
`CDCLatencyTarget` and require lag ≈ 0 before switching over.

---

## 7. Exit criteria for the soak

Close the migration when **all** hold:

- [ ] No R1–R9 rollback trigger fired for 7 consecutive days.
- [ ] `smoke-test.sql` passes at T+1 h, T+24 h and T+7 days.
- [ ] Application error rate at or below the pre-migration baseline.
- [ ] Query latency steady after `ANALYZE`, with no unexplained sequential scans on `books` or `listings`.
- [ ] Full-text search confirmed using `books_text_idx`, and `rows_with_stale_search_text` = 0.
- [ ] No identity/duplicate-key errors recorded.
- [ ] Autovacuum running; no runaway dead tuples or bloat.
- [ ] Final archival Oracle backup taken and retained, and decommissioning signed off in writing.
