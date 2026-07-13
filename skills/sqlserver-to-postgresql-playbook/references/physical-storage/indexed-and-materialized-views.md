# Indexed View Functionality

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.storage.materializedviews.html

**Conversion category:** Manual (Two-star feature compatibility — different paradigm and syntax will require rewriting the application)
**SCT automation:** N/A (No automation)

## SQL Server

The first index created on a view must be a clustered index. Subsequent indexes can be non-clustered indexes.

Before creating an index on a view, the following requirements must be met:

- The `WITH SCHEMABINDING` option must be used when creating the view.
- Verify the `SET` options are correct for all existing tables referenced in the view and for the session.
- Ensure that a clustered index on the view exists.

Note: You can't use indexed views with temporal queries (`FOR SYSTEM_TIME`).

```sql
SET NUMERIC_ROUNDABORT OFF;
SET ANSI_PADDING, ANSI_WARNINGS, CONCAT_NULL_YIELDS_NULL, ARITHABORT,
  QUOTED_IDENTIFIER, ANSI_NULLS ON;
GO

CREATE VIEW Sales.Ord_view
WITH SCHEMABINDING
AS
  SELECT SUM(Price*Qty*(1.00-Discount)) AS Revenue,
    OrdTime, ID, COUNT_BIG(*) AS COUNT
  FROM Sales.OrderDetail AS ordet, Sales.OrderHeader AS ordhead
  WHERE ordet.SalesOrderID = ordhead.SalesOrderID
  GROUP BY OrdTime, ID;
GO

CREATE UNIQUE CLUSTERED INDEX IDX_V1
  ON Sales.Ord_view (OrdTime, ID);
GO
```

For more information, see [Create Indexed Views](https://docs.microsoft.com/en-us/sql/relational-databases/views/create-indexed-views?view=sql-server-2017) in the SQL Server documentation.

## PostgreSQL

PostgreSQL doesn't support indexed views, but provides similar functionality with materialized views. You run queries associated with materialized views, and populate the view data with the `REFRESH` command.

The PostgreSQL implementation of materialized views has three primary limitations:

- You can refresh materialized views either manually or via a job running `REFRESH MATERIALIZED VIEW`. To refresh automatically, create a trigger.
- Materialized views only support complete (full) refresh.
- DML on materialized views isn't supported.

When tables are big, a full `REFRESH` can cause performance issues. In that case, use triggers to sync from one table to a new table and use the new table as an indexed view.

```sql
CREATE MATERIALIZED VIEW sales_summary AS
SELECT seller_no,sale_date,sum(sale_amt)::numeric(10,2) as sales_amt
FROM sales
WHERE sale_date < CURRENT_DATE
GROUP BY seller_no, sale_date
ORDER BY seller_no, sale_date;
```

Manual refresh:

```sql
REFRESH MATERIALIZED VIEW sales_summary;
```

Note: Materialized view data isn't refreshed automatically when underlying tables change. For automatic refresh, create a trigger on the underlying tables.

A materialized view uses a regular database table underneath, so you can create indexes on it directly to improve query performance:

```sql
CREATE UNIQUE INDEX sales_summary_seller
ON sales_summary (seller_no, sale_date);
```

Automatic refresh via trigger:

```sql
CREATE OR REPLACE FUNCTION refresh_mv1()
returns trigger language plpgsql as
$$ begin
refresh materialized view mv1;
return null;
end $$;
```

Then create the `refresh_mv1` trigger after insert, update, delete, or truncate on the underlying table, running `refresh_mv1();` for each statement.

For more information, see [Materialized Views](https://www.postgresql.org/docs/13/rules-materializedviews.html) in the PostgreSQL documentation.

## Conversion notes

- SQL Server indexed views are automatically refreshed and support DML on underlying tables transparently; PostgreSQL materialized views are refreshed manually (or via trigger) and only support full refresh.
- DML directly against the view: supported (indirectly via base tables) for SQL Server indexed views; not supported for PostgreSQL materialized views.
- Refresh strategy: SQL Server = automatic; PostgreSQL = manual or trigger-driven. Trigger-based auto-refresh can be expensive on large/high-DML tables — consider scheduled refreshes or a sync-table pattern instead.
- This is a paradigm shift requiring application changes; no SCT automation is available.

### Feature comparison

| Feature | SQL Server (Indexed views) | PostgreSQL (Materialized view) |
|---|---|---|
| Index refresh | Automatic | Manual (can be automated with triggers) |
| DML | Supported | Not supported |
| Create | `CREATE VIEW ... WITH SCHEMABINDING` + `CREATE UNIQUE CLUSTERED INDEX` | `CREATE MATERIALIZED VIEW ... AS SELECT ...` |
