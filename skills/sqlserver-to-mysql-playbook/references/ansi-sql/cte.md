# Common Table Expressions for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.cte.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** No automation

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): CTEs are native on 3 / 8.4 (verified); RECURSIVE keyword, anchor column widths (1406), MAXRECURSION → cte_max_recursion_depth (3636), no updatable CTEs (1288) — all verified; 5.7 workarounds moved to a legacy section.

**Key differences:** On Aurora MySQL 3 / 8.4, `WITH` and `WITH RECURSIVE` are native (verified); add the `RECURSIVE` keyword, widen anchor columns, and replace `MAXRECURSION` with `cte_max_recursion_depth`. *(Corrected: the playbook's derived-table/loop rewrite applied to Aurora MySQL 5.7 only.)* The conversion category above is the playbook's 5.7 rating; on 3 / 8.4 most CTE code is Assisted.

## SQL Server

CTEs (ANSI since SQL:1999) define a temporary named result set. Can be the target of DML (like updatable views). Support recursion per ANSI 99.

### Simplified CTE Syntax
```sql
WITH <CTE NAME>
AS
(
SELECT ....
)
SELECT ...
FROM CTE
```

### Recursive CTE Syntax
```sql
WITH <CTE NAME>
AS (
<Anchor SELECT query>
UNION ALL
<Recursive SELECT query with reference to <CTE NAME>>
)
SELECT ... FROM <CTE NAME>...
```

### Example (non-recursive)
```sql
WITH AggregatedOrders
AS
(
    SELECT OrderID, SUM(Quantity) AS TotalQty
    FROM OrderItems
    GROUP BY OrderID
)
SELECT O.OrderID, O.Item, O.Quantity,
    (O.Quantity / AO.TotalQty) * 100 AS PercentOfOrder
FROM OrderItems AS O
    INNER JOIN
    AggregatedOrders AS AO
    ON O.OrderID = AO.OrderID;
```

### Example (recursive)
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
SELECT *
FROM EmpHierarchyCTE;
```

## MySQL
**Aurora MySQL 3 and 8.4 support non-recursive and recursive CTEs** (`WITH`, `WITH RECURSIVE`, verified on 3.13.0 and 8.4.8). Most SQL Server CTEs convert with syntax changes only:

```sql
-- SQL Server: WITH Org AS (… UNION ALL …) SELECT … OPTION (MAXRECURSION 500)
WITH RECURSIVE org (employee, manager, lvl, path) AS (
  SELECT employee, direct_manager, 0, CAST(employee AS CHAR(1000))
  FROM employees WHERE direct_manager IS NULL
  UNION ALL
  SELECT e.employee, e.direct_manager, o.lvl + 1, CONCAT(o.path, '/', e.employee)
  FROM employees e JOIN org o ON e.direct_manager = o.employee)
SELECT * FROM org ORDER BY path;
```

Differences from SQL Server (verified):
- MySQL requires the **`RECURSIVE`** keyword for a self-referencing CTE.
- **Column types come from the anchor member**: a growing string column fails with *Data too long* (error 1406) unless the anchor casts it wide (`CAST(… AS CHAR(1000))`); that error needs `STRICT_TRANS_TABLES`. Under Aurora's default (empty) `sql_mode` there is no error and no warning: the string is silently truncated to the anchor width (`'a-x-x-x'` comes back as `'a'`, verified on 3.13.0 and 8.4.8).
- `OPTION (MAXRECURSION n)` → `SET SESSION cte_max_recursion_depth = n` (default 1000; error 3636 when exceeded). `MAXRECURSION 0` (unlimited) → a large value plus a level guard.
- A CTE **cannot be the target** of `UPDATE`/`DELETE` (error 1288); SQL Server's `WITH c AS (…) UPDATE c SET …` → `UPDATE t JOIN c ON … SET t.col = …` (multi-table update with a CTE works, verified).
- No `SEARCH`/`CYCLE` clauses; stop cycles with a path check (`FIND_IN_SET`).

### Legacy: Aurora MySQL 5.7 workarounds
Only needed on Aurora MySQL 2 (5.7, past standard support):

### Replacing non-recursive CTEs with a derived table
```sql
SELECT O.OrderID,
    O.Item,
    O.Quantity,
    (O.Quantity / AO.TotalQty) * 100 AS PercentOfOrder
FROM OrderItems AS O
    INNER JOIN
    (
        SELECT OrderID,
        SUM(Quantity) AS TotalQty
        FROM OrderItems
        GROUP BY OrderID
    ) AS AO
    ON O.OrderID = AO.OrderID;
```
Note: the derived table definition must be repeated for each instance required by the query.

### Replacing recursive CTEs with a loop in a stored procedure
Stored procedure/function recursion is OFF by default; set `max_sp_recursion_depth >= 1` to enable (not recommended due to thread stack contention).

```sql
CREATE PROCEDURE P()
BEGIN
DECLARE var_lvl INT;
DECLARE var_Employee VARCHAR(5);
SET var_lvl = 0;
SET var_Employee = (
    SELECT Employee FROM Employees WHERE DirectManager IS NULL
);
INSERT INTO EmpHierarchy VALUES (var_lvl, var_Employee, NULL);
WHILE var_lvl <> -1
DO
INSERT INTO EmpHierarchy (LVL, Employee, Manager)
SELECT var_lvl + 1, Employee, DirectManager
FROM Employees
WHERE DirectManager IN (
    SELECT Employee FROM EmpHierarchy WHERE LVL = var_lvl
);
IF NOT EXISTS (
    SELECT * FROM EmpHierarchy WHERE LVL = var_lvl + 1
)
THEN SET var_lvl = -1;
ELSE SET var_lvl = var_lvl + 1;
END IF;
END WHILE;
END;
```

## Conversion notes

| SQL Server | Aurora MySQL | Comments |
|---|---|---|
| Non-recursive CTE | `WITH` (native) | 5.7 only: derived table |
| Recursive CTE | `WITH RECURSIVE` (native) | widen growing anchor columns; `cte_max_recursion_depth` |
| Updatable CTE | not supported | multi-table `UPDATE … JOIN cte` |
- Convert CTEs natively on Aurora MySQL 3 / 8.4; the derived-table and loop workarounds are legacy.
