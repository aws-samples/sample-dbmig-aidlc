# Oracle Materialized Views and MySQL Summary Tables or Views

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.matviews.html

**Conversion category:** Manual (one-star feature compatibility) — MySQL does not support materialized views.
**SCT automation:** No automation. SCT action code index: Materialized Views.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Still no MVs on 3 / 8.4; atomic RENAME refresh, trigger-maintenance cost, zero-ETL + Redshift MVs, no query rewrite.

## Oracle

Materialized views are table segments whose contents are periodically refreshed from a stored query. Useful for cross-database replication, data warehousing, and persisting complex query results. Source objects are called master/detail tables.

Key options:
- **Build:** `BUILD IMMEDIATE` (populate on creation) vs deferred (populate on first refresh).
- **Refresh type:** `REFRESH FAST` (incremental; requires materialized view logs) vs `COMPLETE` (truncate and repopulate).
- **Materialized view logs:** record DML changes on master tables for faster (fast) refreshes; without them only complete refresh is possible.
- **Refresh strategy:** `ON COMMIT` (refresh on commit to base tables) vs `ON DEMAND` (scheduled or manual).

Simple materialized view:

```sql
CREATE MATERIALIZED VIEW mv1 AS SELECT * FROM hr.employees;
```

Materialized view over a database link with a subquery, updatable:

```sql
CREATE MATERIALIZED VIEW foreign_customers FOR
UPDATE AS SELECT * FROM sh.customers@remote cu WHERE EXISTS
(SELECT * FROM sh.countries@remote co WHERE co.country_id = cu.country_id);
```

Fast-refresh on commit, with materialized view logs:

```sql
CREATE MATERIALIZED VIEW LOG ON times
WITH ROWID, SEQUENCE (time_id, calendar_year)
INCLUDING NEW VALUES;

CREATE MATERIALIZED VIEW LOG ON products
WITH ROWID, SEQUENCE (prod_id)
INCLUDING NEW VALUES;

CREATE MATERIALIZED VIEW sales_mv
BUILD IMMEDIATE
REFRESH FAST ON COMMIT
AS SELECT t.calendar_year, p.prod_id,
SUM(s.amount_sold) AS sum_sales
FROM times t, products p, sales s
WHERE t.time_id = s.time_id AND p.prod_id = s.prod_id
GROUP BY t.calendar_year, p.prod_id;
```

## MySQL

Aurora MySQL has no materialized view feature. Combine other features to approximate it:

- **Summary tables** — store pre-computed results in regular tables and query them directly; keep them updated via triggers or events.
- **Views** — regular views (no stored results), optionally combined with Aurora Parallel Query, which offloads query work to the storage layer and can greatly improve performance. Measure SQL performance to decide.

```sql
-- summary table refreshed by an event (emulating ON DEMAND / scheduled refresh)
CREATE EVENT refresh_sales_summary ON SCHEDULE EVERY 1 HOUR DO
  -- e.g., REPLACE INTO sales_summary SELECT ... ;
  CALL refresh_sales_summary_proc();
```

## Conversion notes

- No direct equivalent — choose between **summary tables** (materialized data, refreshed by triggers/events) and **plain views** (live, no storage) per use case.
- `REFRESH FAST ON COMMIT` (incremental on base-table change) is emulated with **AFTER INSERT/UPDATE/DELETE triggers** maintaining the summary table.
- `REFRESH ... ON DEMAND` / scheduled refresh is emulated with a MySQL `EVENT` rebuilding the summary table.
- Materialized views over database links have no equivalent (MySQL lacks DB links); re-architect via replication / AWS DMS / application.
- Consider Aurora Parallel Query before building summary tables if a plain view is fast enough.
- Still no materialized views on Aurora MySQL 3 or 8.4. Refresh pattern for `COMPLETE` refresh without blocking readers: build into `mv_new`, then `RENAME TABLE mv TO mv_old, mv_new TO mv; DROP TABLE mv_old;` (atomic rename).
- Trigger-maintained summaries serialize writers on the summary rows and add latency to every base-table DML; use them only for small aggregates. Triggers cannot call dynamic SQL or commit (verified).
- For heavy reporting, an Aurora zero-ETL integration to Amazon Redshift (supported on 3.x and 8.4) with Redshift materialized views is often a better fit than in-database summary tables.
- Query rewrite (`ENABLE QUERY REWRITE`) has no equivalent: change queries to read the summary table explicitly.
