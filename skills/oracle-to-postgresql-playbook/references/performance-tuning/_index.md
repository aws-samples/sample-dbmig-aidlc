# Performance Tuning — Reference Index

Oracle → Aurora PostgreSQL migration references for performance tuning, distilled from the AWS Oracle→Aurora PostgreSQL Migration Playbook.

- [hints-and-query-planning.md](hints-and-query-planning.md) — Oracle's 60+ inline optimizer hints vs. PostgreSQL planning parameters (`enable_seqscan`, `enable_nestloop`, `random_page_cost`), `pg_hint_plan` comment hints (available on Aurora 18), and QPM. Default: drop hints and re-add only proven ones.
- [run-plans.md](run-plans.md) — Reading execution plans: Oracle `EXPLAIN PLAN`/`AUTOTRACE` vs. PostgreSQL `EXPLAIN`/`EXPLAIN ANALYZE`, operator mapping (`TABLE ACCESS FULL` → `Seq Scan`), and Aurora PostgreSQL Query Plan Management (QPM).
- [table-statistics.md](table-statistics.md) — Collecting optimizer statistics: Oracle `DBMS_STATS` and automatic collection vs. PostgreSQL `ANALYZE` and the autovacuum daemon, including sampling/granularity differences.
