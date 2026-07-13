# Common Table Expressions for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.cte.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** No automation

**Key differences:** Rewrite non-recursive CTE to use views and derived tables. Redesign recursive CTE code. (Applies to Aurora MySQL 5.7; RDS for MySQL 8 supports CTEs.)

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

Aurora MySQL 5.7 does NOT support CTEs. (RDS for MySQL 8 supports both recursive and non-recursive CTEs, including `LIMIT`/`OFFSET` in recursive parts as of 8.0.19.)

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
| Non-recursive CTE | Derived table | Derived table definition subquery must be repeated for multiple instances. |
| Recursive CTE | Loop inside a stored procedure or function | |

- Aurora MySQL 5.7 has no CTE support — RDS for MySQL 8 does.
- Non-recursive CTEs → views or derived tables (subquery in `FROM`).
- Recursive CTEs → loops; archive original code for potential reuse under MySQL 8.
