# PIVOT and UNPIVOT for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.pivot.html

**Conversion category:** Manual (Three star feature compatibility — no automation; straightforward rewrite)
**SCT automation:** No automation

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Still no PIVOT/UNPIVOT (verified); added a verified LATERAL UNPIVOT that drops NULLs like SQL Server, NULL caveat for the original rewrite, dynamic pivot via GROUP_CONCAT + PREPARE, alias quoting.

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
- Pivoted column lists are static — you must enumerate each output column manually. A dynamic pivot (T-SQL built with `STUFF(… FOR XML PATH)` + `sp_executesql`) → build the column list with `GROUP_CONCAT` (raise `group_concat_max_len`) into a `PREPARE`d statement inside a procedure.
- Still no `PIVOT`/`UNPIVOT` on Aurora MySQL 3 / 8.4 (syntax error, verified).

Verified on Aurora MySQL 3.13 and 8.4.8 — preferred UNPIVOT form with `LATERAL` (MySQL 8.0.14+):

```sql
SELECT e.SaleDate, v.Employee, v.SaleAmount
FROM EmployeeSales e
CROSS JOIN LATERAL (
    SELECT 'John' AS Employee, e.John AS SaleAmount
    UNION ALL SELECT 'Kevin', e.Kevin
    UNION ALL SELECT 'Mary',  e.Mary) AS v
WHERE v.SaleAmount IS NOT NULL;   -- SQL Server UNPIVOT drops NULLs; the CROSS JOIN version above keeps them
```
- The `CROSS JOIN … CASE` UNPIVOT in the original **keeps NULL values** as rows; add `WHERE SaleAmount IS NOT NULL` for SQL Server equivalence.
- Quote numeric pivot column aliases with backticks (`` AS `1` ``) rather than single quotes; single-quoted aliases are accepted but are string literals elsewhere.
- `COUNT(*) FILTER (WHERE …)` does not exist in MySQL; keep the `COUNT(CASE … END)` / `SUM(CASE … END)` form.
