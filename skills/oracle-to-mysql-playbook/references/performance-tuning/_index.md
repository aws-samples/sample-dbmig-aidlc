# Performance Tuning — Reference Index

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> Section: Performance tuning (Oracle 19c → Amazon Aurora MySQL)

Granular reference files distilled from the AWS playbook's performance-tuning chapter, covering optimizer-related features and their Oracle→Aurora MySQL conversion considerations.

| File | Topic | Conversion category | Compatibility |
|---|---|---|---|
| [database-hints.md](database-hints.md) | Database hints (index hints, optimizer hints) | Assisted | ★★ |
| [run-plans.md](run-plans.md) | Run plans (`EXPLAIN` / `EXPLAIN PLAN`) | Assisted | ★★ |
| [table-statistics.md](table-statistics.md) | Table statistics management (`DBMS_STATS` → `ANALYZE TABLE`) | Assisted | ★★★ |

## Summary

- **Database hints**: MySQL has a very limited hint set vs. Oracle's 60+. Use `USE`/`IGNORE`/`FORCE INDEX` index hints and `/*+ ... */` optimizer hints. Start migration with hints removed; reapply only as a last resort.
- **Run plans**: Both engines provide an explain facility, but the optimizers are completely different. Oracle uses `EXPLAIN PLAN` / `AUTOTRACE`; MySQL uses `EXPLAIN` / `DESCRIBE` (plus `EXPLAIN ANALYZE` in 8.0.18+).
- **Table statistics**: Oracle's rich `DBMS_STATS` (column-level, histograms, multiple levels) maps to Aurora MySQL's table-level, index-only statistics (`ANALYZE TABLE`, `STATS_PERSISTENT`, `STATS_AUTO_RECALC`, `STATS_SAMPLE_PAGES`). No histograms — density only.
