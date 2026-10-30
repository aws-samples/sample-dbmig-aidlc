# Materialized Views

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.matviews.html

**Conversion category:** Assisted (Three-star feature compatibility, three-star automation)
**SCT automation:** SCT action code index: Materialized Views. Key difference: PostgreSQL doesn't support automatic or incremental REFRESH.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): `REFRESH … CONCURRENTLY` (unique index required, verified), `WITH NO DATA`, `MAINTAIN` privilege, `pg_cron` scheduling, `pg_ivm` unavailable, trigger-maintained summary tables for fast-refresh MViews.

## Oracle

Oracle materialized views (MViews) store a pre-computed query result as a table segment, refreshed periodically. Useful for replication, data warehousing, and persisting complex query results. Source objects = master tables (replication) / detail tables (DW).

Key options:
- **BUILD IMMEDIATE** — populate now (vs deferred, populated on first refresh).
- **REFRESH FAST** — incremental; only changed rows; requires materialized view logs.
- **COMPLETE** — truncate and repopulate via the query.
- **Materialized view logs** — record DML changes on master tables for faster (fast) refresh; without them Oracle does a complete refresh each time.
- Refresh strategy: **ON COMMIT** (refresh on any commit to underlying tables) or **ON DEMAND** (scheduled/manual).

```sql
-- simple
CREATE MATERIALIZED VIEW mv1 AS SELECT * FROM hr.employees;

-- complex, over a database link, updatable
CREATE MATERIALIZED VIEW foreign_customers FOR
UPDATE AS SELECT * FROM sh.customers@remote cu WHERE EXISTS
(SELECT * FROM sh.countries@remote co WHERE co.country_id = cu.country_id);

-- fast refresh on commit, requires MV logs
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

Manual refresh: `DBMS_MVIEW.REFRESH('mv1', 'cf');` (`c` = complete, `f` = fast).

## PostgreSQL

PostgreSQL supports materialized views but with three key limitations vs Oracle:
- Refresh is **manual or job-driven** (`REFRESH MATERIALIZED VIEW`); automatic refresh requires a trigger.
- **Only complete (full) refresh** — no incremental/fast refresh.
- **DML on materialized views is not supported.**

**`REFRESH MATERIALIZED VIEW CONCURRENTLY`** rebuilds without blocking readers (closest to Oracle's online complete refresh). It requires a **unique index without a `WHERE` clause** on the MView (verified: fails with a hint otherwise). `WITH NO DATA` creates an unpopulated MView that errors on `SELECT` until refreshed (verified), like Oracle `BUILD DEFERRED`. The `MAINTAIN` privilege (PG 17, `GRANT MAINTAIN ON mv TO role`) lets a non-owner refresh it.

```sql
CREATE MATERIALIZED VIEW sales_summary AS
SELECT seller_no,sale_date,sum(sale_amt)::numeric(10,2) as sales_amt
FROM sales
WHERE sale_date < CURRENT_DATE
GROUP BY seller_no, sale_date
ORDER BY seller_no, sale_date;

REFRESH MATERIALIZED VIEW sales_summary;

-- index directly on the MView (uses a regular table underneath)
CREATE UNIQUE INDEX sales_summary_seller
ON sales_summary (seller_no, sale_date);
```

Automatic refresh can use a trigger on underlying tables. This refreshes the whole MView on **every** write statement, so use it only for small, rarely written sources. Prefer a scheduled `pg_cron` job (`SELECT cron.schedule('mv1', '*/5 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv1')`):
```sql
CREATE OR REPLACE FUNCTION refresh_mv1()
returns trigger language plpgsql as
$$ begin
refresh materialized view mv1;
return null;
end $$;

create trigger refresh_mv1 after insert or update
or delete or truncate on employees for each statement
execute function refresh_mv1();
```

### Summary mapping

| Option | Oracle | PostgreSQL |
|---|---|---|
| Create MView | `CREATE MATERIALIZED VIEW mv1 AS SELECT * FROM employees;` | `CREATE MATERIALIZED VIEW mv1 AS SELECT * FROM employees;` |
| Manual refresh | `DBMS_MVIEW.REFRESH('mv1', 'cf');` | `REFRESH MATERIALIZED VIEW mv1;` |
| Online refresh | `CREATE MATERIALIZED VIEW mv1 REFRESH FAST ON COMMIT AS ...` | `REFRESH MATERIALIZED VIEW CONCURRENTLY mv1` (needs a unique index) on a `pg_cron` schedule, or a trigger after DML |
| Deferred build | `BUILD DEFERRED` | `WITH NO DATA`, then `REFRESH` |
| Automatic incremental refresh | `CREATE MATERIALIZED VIEW LOG ... INCLUDING NEW VALUES; CREATE MATERIALIZED VIEW mv1 REFRESH FAST AS ...` | Not Supported |
| DML on MView data | Supported | Not Supported |

## Conversion notes
- PostgreSQL has **no fast/incremental refresh** and **no ON COMMIT auto-refresh**. The `pg_ivm` extension is **not** available on Aurora 18. For `REFRESH FAST ON COMMIT` aggregates over large tables, convert to a **summary table maintained by triggers** (incremental, exact) and record it as a design change. Otherwise schedule `REFRESH … CONCURRENTLY`.
- Always create a unique index on converted MViews so `CONCURRENTLY` is possible.
- **No DML** allowed on PostgreSQL materialized views (Oracle allows it via FOR UPDATE).
- Add indexes directly on the materialized view to speed queries.
- Materialized view logs have no PostgreSQL equivalent.
