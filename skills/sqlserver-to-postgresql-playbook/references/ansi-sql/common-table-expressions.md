# Common Table Expressions (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.cte.html

**Conversion category:** Automatic (Five-star compatibility, five-star automation)
**SCT automation:** N/A. Key difference: use the `RECURSIVE` keyword for recursive CTE queries in PostgreSQL.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): integer division is the same in both engines (corrected); `AVG(int)` return type differs (verified); `MAXRECURSION`, `SEARCH`/`CYCLE`, `MATERIALIZED`, DML through a CTE.

## SQL Server

CTEs (ANSI SQL:1999) define a temporary named result set referenced by a subsequent query. Can be the target of DML (like updatable views). Recursive CTEs reference themselves.

Syntax:
```sql
WITH <CTE NAME>
AS
(
SELECT ....
)
SELECT ...
FROM CTE
```

Recursive syntax (no `RECURSIVE` keyword needed):
```sql
WITH <CTE NAME>
AS (
<Anchor SELECT query>
UNION ALL
<Recursive SELECT query with reference to <CTE NAME>>
)
SELECT ... FROM <CTE NAME>...
```

Example — relative quantity per item:
```sql
WITH AggregatedOrders
AS
( SELECT OrderID, SUM(Quantity) AS TotalQty
FROM OrderItems
GROUP BY OrderID
)
SELECT O.OrderID, O.Item,
O.Quantity,
(O.Quantity / AO.TotalQty) * 100 AS PercentOfOrder
FROM OrderItems AS O
INNER JOIN
AggregatedOrders AS AO
ON O.OrderID = AO.OrderID;
```

Recursive example — employee hierarchy:
```sql
WITH EmpHierarchyCTE AS
(
  SELECT 0 AS LVL, Employee, DirectManager
  FROM Employees AS E
  WHERE DirectManager IS NULL
  UNION ALL
  SELECT LVL + 1 AS LVL, E.Employee, E.DirectManager
  FROM EmpHierarchyCTE AS EH
  INNER JOIN Employees AS E
  ON E.DirectManager = EH.Employee
)
SELECT * FROM EmpHierarchyCTE;
```

## PostgreSQL

PostgreSQL conforms to ANSI SQL-99. A CTE (`WITH` query) statement can be `SELECT`, `INSERT`, `UPDATE`, or `DELETE`.

Syntax:
```sql
WITH <CTE NAME>
AS
(
SELECT OR DML
)
SELECT OR DML
```

Recursive syntax — requires the `RECURSIVE` keyword:
```sql
WITH RECURSIVE <CTE NAME>
AS (
<Anchor SELECT query>
UNION ALL
<Recursive SELECT query with reference to <CTE NAME>>
)
SELECT OR DML
```

Recursive example:
```sql
WITH RECURSIVE t(n) AS (
  VALUES (0)
  UNION ALL
  SELECT n+1 FROM t WHERE n < 5)
SELECT * FROM t;
```

Recursive employee hierarchy (note added `RECURSIVE`):
```sql
WITH RECURSIVE EmpHierarchyCTE AS
(
SELECT 0 AS LVL, Employee, DirectManager
FROM Employees AS E
WHERE DirectManager IS NULL
UNION ALL
SELECT LVL + 1 AS LVL, E.Employee, E.DirectManager
FROM EmpHierarchyCTE AS EH
INNER JOIN Employees AS E
ON E.DirectManager = EH.Employee
)
SELECT * FROM EmpHierarchyCTE;
```

## Conversion notes
- Add the `RECURSIVE` keyword to all recursive CTEs; SQL Server does not require it but PostgreSQL does. The SQL Server recursive form gives undesired results in PostgreSQL.
- Integer division: `INT / INT` truncates in **both** engines (`7/2 = 3`, verified), so the percent-of-order example returns `0` on SQL Server too unless a column is decimal. The real difference is in aggregates: `AVG(int)` returns an **int** in SQL Server but **numeric** in PostgreSQL (`avg(1,2) = 1.5000000000000000`, verified), and `SUM(int)` returns `bigint`. Cast explicitly where results are compared. To get fractional results:
  ```sql
  trunc((O.Quantity::decimal / AO.TotalQty::decimal)*100,2) AS PercentOfOrder
  ```
- Non-recursive CTE syntax is otherwise identical.
- `OPTION (MAXRECURSION n)` has no equivalent; PostgreSQL has no recursion limit. Add a depth column with `WHERE lvl < n`, or use `CYCLE id SET is_cycle USING path` (PG 14+) to stop on cycles. `SEARCH DEPTH FIRST BY col SET ord` / `SEARCH BREADTH FIRST` (PG 14+) produce hierarchy ordering without hand-built path strings.
- Since PG 12, single-reference CTEs are inlined. Use `AS MATERIALIZED` to force one evaluation (SQL Server never materializes CTEs).
- DML **through** a CTE (`WITH c AS (SELECT …) UPDATE c SET …`, valid in SQL Server) is not allowed in PostgreSQL. Rewrite as `UPDATE t SET … FROM (…) c WHERE …`. PostgreSQL instead supports data-modifying CTEs (`WITH d AS (DELETE … RETURNING *) …`).
