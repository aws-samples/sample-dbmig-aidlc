# PIVOT and UNPIVOT

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.pivot.html

**Conversion category:** Assisted (three-star feature compatibility, no automation — straightforward manual rewrite)
**SCT automation:** No automation; SCT action code index: PIVOT and UNPIVOT

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

UNPIVOT → `CROSS JOIN` with a set of column names + `CASE`:

```sql
SELECT SaleDate, Employee, SaleAmount
FROM (
  SELECT SaleDate, Employee,
    CASE
      WHEN Employee = 'John' THEN 'John'
      WHEN Employee = 'Kevin' THEN 'Kevin'
      WHEN Employee = 'Mary' THEN 'Mary'
    END AS SaleAmount
  FROM EmployeeSales as emp
  CROSS JOIN
  (
    SELECT 'John' AS Employee
    UNION ALL SELECT 'Kevin'
    UNION ALL SELECT 'Mary'
  ) AS Employees
) AS UnpivotedSet;
```

## Conversion notes
- No PIVOT/UNPIVOT operators — rewrite is straightforward but manual (no automation).
- PIVOT → `GROUP BY` + conditional aggregation (`COUNT/SUM(CASE WHEN ... THEN ... END)`).
- UNPIVOT → `CROSS JOIN` against a derived set of column names, or use `UNION ALL`, or the `unnest()` function.
- Pivoted column lists must be static (known at write time); for dynamic pivots build the SQL with dynamic SQL.
- Consider the `tablefunc` extension's `crosstab()` as an alternative for PIVOT.
