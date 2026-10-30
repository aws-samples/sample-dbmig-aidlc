# PIVOT and UNPIVOT

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.pivot.html

**Conversion category:** Assisted (three-star feature compatibility, no automation — straightforward manual rewrite)
**SCT automation:** No automation; SCT action code index: PIVOT and UNPIVOT

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Fixed the wrong UNPIVOT example (returned names, kept NULLs); added verified FILTER-based PIVOT and LATERAL VALUES UNPIVOT; crosstab NULL-vs-0 difference.

## SQL Server

`PIVOT` and `UNPIVOT` rotate rows into columns and vice versa. In PIVOT, the *anchor column* is not pivoted (one row per unique value, like GROUP BY); pivoted columns come from the PIVOT clause with values from an aggregate.

PIVOT syntax:

```sql
SELECT <Anchor column>,
  [Pivoted Column 1] AS <Alias>,
  [Pivoted column 2] AS <Alias> ...n
FROM
  (<SELECT Statement of Set to be Pivoted>) AS <Set Alias>
PIVOT
(
  <Aggregate Function>(<Aggregated Column>)
FOR [<Column With the Values for the Pivoted Columns Names>]
  IN ( [Pivoted Column 1], [Pivoted column 2] ...)
) AS <Pivot Table Alias>;
```

PIVOT example — orders per day per customer:

```sql
SELECT Customer, [1], [2], [3], [4] /*...[31]*/
FROM (
  SELECT OrderID, Customer, DAY(OrderDate) AS OrderDay FROM Orders
  ) AS SourceSet
PIVOT
(
  COUNT(OrderID) FOR OrderDay IN ([1], [2], [3], [4] /*...[31]*/)
) AS PivotSet;
```

UNPIVOT — spreads column values into rows (no aggregation needed):

```sql
SELECT SaleDate, Employee, SaleAmount
FROM
( SELECT SaleDate, John, Kevin, Mary FROM EmployeeSales ) AS SourceSet
UNPIVOT (
  SaleAmount FOR Employee IN (John, Kevin, Mary)
  ) AS UnpivotSet;
```

## PostgreSQL

Aurora PostgreSQL does **not** support `PIVOT`/`UNPIVOT`. Rewrite using standard SQL.

PIVOT → conditional aggregation with `CASE`:

```sql
SELECT Customer,
COUNT(CASE WHEN date_part('day', OrderDate) = 1 THEN 'OrderDate' ELSE NULL END) AS "1",
COUNT(CASE WHEN date_part('day', OrderDate) = 2 THEN 'OrderDate' ELSE NULL END) AS "2",
COUNT(CASE WHEN date_part('day', OrderDate) = 3 THEN 'OrderDate' ELSE NULL END) AS "3",
COUNT(CASE WHEN date_part('day', OrderDate) = 4 THEN 'OrderDate' ELSE NULL END) AS "4" /*...[31]*/
FROM Orders AS O
GROUP BY Customer;
```

Preferred PIVOT form — the SQL-standard `FILTER` clause (verified on Aurora PostgreSQL 18.6; returns `0` for an empty bucket, exactly like `PIVOT … COUNT`):

```sql
SELECT Customer,
  COUNT(*) FILTER (WHERE extract(day FROM OrderDate) = 1) AS "1",
  COUNT(*) FILTER (WHERE extract(day FROM OrderDate) = 2) AS "2" /* … "31" */
FROM Orders
GROUP BY Customer;
```

UNPIVOT → `CROSS JOIN LATERAL (VALUES …)` (verified on 18.6):

```sql
SELECT e.SaleDate, v.Employee, v.SaleAmount
FROM EmployeeSales e
CROSS JOIN LATERAL (VALUES ('John', e.John), ('Kevin', e.Kevin), ('Mary', e.Mary))
     AS v(Employee, SaleAmount)
WHERE v.SaleAmount IS NOT NULL;   -- UNPIVOT drops NULL values; keep this filter for equivalence
```

> Correction: the original playbook's UNPIVOT example returned the employee **name** in `SaleAmount` (`THEN 'John'` instead of the `John` column) and kept NULL rows. Use the `LATERAL (VALUES …)` form above.

## Conversion notes
- No PIVOT/UNPIVOT operators — rewrite is straightforward but manual (no automation).
- PIVOT → `GROUP BY` + conditional aggregation (`COUNT/SUM(CASE WHEN ... THEN ... END)`).
- PIVOT → `agg(…) FILTER (WHERE …)` per pivoted column (preferred) or `agg(CASE WHEN … END)`.
- UNPIVOT → `CROSS JOIN LATERAL (VALUES (…), …)` with `WHERE value IS NOT NULL`. All listed columns must share one type; cast where SQL Server would have required the same.
- Pivoted column names that are numbers or mixed-case (`[1]`, `[Mary]`) need double quotes in PostgreSQL.
- Pivoted column lists must be static (known at write time); for dynamic pivots build the SQL with dynamic SQL.
- `tablefunc` `crosstab(source_sql, category_sql)` is available on 18.6 and works, but you must declare the output column list, and missing buckets come back as `NULL` rather than `0` (verified). Wrap with `coalesce` if it replaces `PIVOT … COUNT`.
