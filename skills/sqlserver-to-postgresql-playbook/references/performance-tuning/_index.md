# Performance Tuning — SQL Server to Aurora PostgreSQL

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> Section: Performance tuning

Reference files distilled from the AWS Migration Playbook performance-tuning chapter. Each file follows the same structure: conversion category, SQL Server usage (with examples), PostgreSQL usage (with examples), and conversion notes.

| File | Topic | Conversion category | Key difference |
|---|---|---|---|
| [run-plans.md](run-plans.md) | Tuning run plans (`SHOWPLAN`/`STATISTICS XML` ↔ `EXPLAIN`/`EXPLAIN ANALYZE`; Aurora QPM) | Manual (two-star) | Completely different optimizers, operators, and rules; plans not portable |
| [query-hints-and-plan-guides.md](query-hints-and-plan-guides.md) | Query/table/join hints and plan guides ↔ session planning parameters | Manual (two-star) | PostgreSQL has no in-query hints; only coarse session-level planner toggles |
| [managing-statistics.md](managing-statistics.md) | Statistics collection (`CREATE/UPDATE STATISTICS` ↔ `ANALYZE`/autovacuum) | Assisted (three-star) | Similar functionality; syntax/option differences |

## Summary

- **Run plans**: SQL Server uses `SHOWPLAN_*`/`STATISTICS XML` (graphical in SSMS) and built-in automatic tuning; PostgreSQL uses `EXPLAIN`/`EXPLAIN ANALYZE` (text/XML/JSON/YAML), with Aurora Query Plan Management (QPM) for plan stability and adaptability.
- **Hints**: SQL Server has rich statement-level JOIN/table/query hints plus plan guides; PostgreSQL exposes only session-level Query Planning Parameters (`ENABLE_SEQSCAN`, `RANDOM_PAGE_COST`/`SEQ_PAGE_COST`, `ENABLE_NESTLOOP`, etc.) — manual rework required.
- **Statistics**: closest mapping of the three. SQL Server `CREATE/UPDATE STATISTICS` + `AUTO_*` options map to PostgreSQL `ANALYZE` + the `AUTOVACUUM` daemon, tuned via `default_statistics_target` and per-table `autovacuum_*` parameters.
