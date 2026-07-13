# PIVOT and UNPIVOT for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.pivot.html

**Conversion category:** Manual (Three star feature compatibility — no automation; straightforward rewrite)
**SCT automation:** No automation

## SQL Server

`PIVOT` and `UNPIVOT` rotate rows into columns and columns into rows. The *anchor* column isn't pivoted (one row per unique value, like `GROUP BY`).

### PIVOT syntax

```sql
SELECT <Anchor column>,
    [Pivoted Column 1] AS <Alias>,
    [Pivoted column 2] AS <Alias> ...n
FROM
    (<SELECT Statement of Set to be Pivoted>) AS <Set Alias>
PIVOT
(
    <Aggregate Function>(<Aggregated Column>)
FOR
[<Column With the Values for the Pivoted Columns Names>]
    IN ( [Pivoted Column 1], [Pivoted column 2] ...)
) AS <Pivot Table Alias>;
```

### PIVOT example

```sql
SELECT Customer,
    [1], [2], [3], [4] /*...[31]*/
FROM (
    SELECT OrderID, Customer, DAY(OrderDate) AS OrderDay
    FROM Orders
    ) AS SourceSet
PIVOT
(
    COUNT(OrderID)
    FOR OrderDay IN ([1], [2], [3], [4] /*...[31]*/)
) AS PivotSet;
```

### UNPIVOT example

```sql
SELECT SaleDate, Employee, SaleAmount
FROM
(
    SELECT SaleDate, John, Kevin, Mary
    FROM EmployeeSales
) AS SourceSet
UNPIVOT (
    SaleAmount
    FOR Employee IN (John, Kevin, Mary)
) AS UnpivotSet;
```

## MySQL

Aurora MySQL does **not** support `PIVOT`/`UNPIVOT`. Rewrite with standard SQL.

### PIVOT rewrite — conditional aggregation with CASE

```sql
SELECT Customer,
    COUNT(CASE WHEN DAY(OrderDate) = 1 THEN 'OrderDate' ELSE NULL END) AS '1',
    COUNT(CASE WHEN DAY(OrderDate) = 2 THEN 'OrderDate' ELSE NULL END) AS '2',
    COUNT(CASE WHEN DAY(OrderDate) = 3 THEN 'OrderDate' ELSE NULL END) AS '3',
    COUNT(CASE WHEN DAY(OrderDate) = 4 THEN 'OrderDate' ELSE NULL END) AS '4' /*...[31]*/
FROM Orders AS O
GROUP BY Customer;
```

### UNPIVOT rewrite — CROSS JOIN with a derived value list + CASE

```sql
SELECT SaleDate, Employee, SaleAmount
FROM
(
    SELECT SaleDate, Employee,
        CASE
            WHEN Employee = 'John' THEN John
            WHEN Employee = 'Kevin' THEN Kevin
            WHEN Employee = 'Mary' THEN Mary
        END AS SaleAmount
    FROM EmployeeSales
    CROSS JOIN
    (
        SELECT 'John' AS Employee
        UNION ALL SELECT 'Kevin'
        UNION ALL SELECT 'Mary'
    ) AS Employees
) AS UnpivotedSet;
```

## Conversion notes

- PIVOT → `GROUP BY` + conditional aggregation (`COUNT`/`SUM` with `CASE`), one expression per target column.
- UNPIVOT → `CROSS JOIN` against a derived table of column-name literals (`SELECT ... UNION ALL ...`) plus a `CASE` to select the matching value.
- Pivoted column lists are static — you must enumerate each output column manually (no dynamic pivot).
