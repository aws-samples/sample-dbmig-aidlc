# Performance Tuning for Aurora MySQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tuning.html

Reference information about query execution plans and query hints in Microsoft SQL Server 2019 and Amazon Aurora MySQL — covering execution plan features, automatic tuning, and supported query hints to help troubleshoot performance, optimize queries, and adapt management strategies during migration.

## Topics

| File | Topic | Conversion category | SCT automation |
|---|---|---|---|
| [plans.md](plans.md) | Tuning Run Plans | Manual (Two star) | N/A |
| [query-hints.md](query-hints.md) | Query Hints and Plan Guides | Manual (Two star) | Three star |

## Summary

- **Run plans:** SQL Server uses `SET SHOWPLAN_*`/`SET STATISTICS XML` (text/XML/graphical); Aurora MySQL uses `EXPLAIN`/`DESCRIBE` and `EXPLAIN ANALYZE` (tabular/JSON/TREE). Completely different optimizers — analysis must be redone, not translated.
- **Hints & plan guides:** Aurora MySQL supports optimizer hints (`/*+ ... */`) and index hints (`USE`/`IGNORE`/`FORCE INDEX`) but has no plan-guide equivalent. SQL Server locking hints, `OPTIMIZE FOR`, and `RECOMPILE` are N/A in Aurora MySQL. Recommended approach: remove all hints first, then reapply selectively only as a last resort.
