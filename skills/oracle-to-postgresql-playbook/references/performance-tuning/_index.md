# Performance Tuning — Reference Index

Oracle → Aurora PostgreSQL migration references for performance tuning, distilled from the AWS Oracle→Aurora PostgreSQL Migration Playbook.

- [hints-and-query-planning.md](hints-and-query-planning.md) — Oracle's 60+ inline optimizer hints vs. PostgreSQL session-level query planning parameters (`ENABLE_SEQSCAN`, `ENABLE_NESTLOOP`, `SEQ_PAGE_COST`, `RANDOM_PAGE_COST`); manual conversion since PostgreSQL has no per-statement hints.
- [run-plans.md](run-plans.md) — Reading execution plans: Oracle `EXPLAIN PLAN`/`AUTOTRACE` vs. PostgreSQL `EXPLAIN`/`EXPLAIN ANALYZE`, operator mapping (`TABLE ACCESS FULL` → `Seq Scan`), and Aurora PostgreSQL Query Plan Management (QPM).
- [table-statistics.md](table-statistics.md) — Collecting optimizer statistics: Oracle `DBMS_STATS` and automatic collection vs. PostgreSQL `ANALYZE` and the autovacuum daemon, including sampling/granularity differences.
