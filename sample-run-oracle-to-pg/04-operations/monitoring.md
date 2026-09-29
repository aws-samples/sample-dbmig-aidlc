> ⚠️ **AI-GENERATED — review before use.** Produced by dbmig-aidlc from this migration's context; validate in a non-production environment before relying on it.

# Monitoring — first 72 h

- Application: 5xx rate, p95 latency of `/fulltextsearch` and `/books`, Hibernate errors in logs.
- Database: `pg_stat_statements` top statements; confirm the full-text query uses `books_text_idx`
  (`EXPLAIN` → Bitmap Index Scan) — a seq scan means the query and index expressions drifted.
- Connections vs pool size; autovacuum on `listings`/`orders`; deadlocks (`inventory_pkg_reduce_inventory` uses `FOR UPDATE`).
- Errors with SQLSTATE `U0001`/`U0002` (converted `RAISE_APPLICATION_ERROR`) — expected business errors.
- Daily: `./dbmig compare` during any dual-run window; identity `next > MAX` (`./dbmig reset-identity` dry run).
