# Common Table Expressions (CTE)

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.cte.html

**Conversion category:** Manual (★★ feature compatibility, no automation) — workaround available
**SCT automation:** Action code "Common Table Expressions"

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): CTEs and recursive CTEs are native on 3 / 8.4 (verified); added a verified CONNECT BY → WITH RECURSIVE pattern, the anchor-column width trap (error 1406), cte_max_recursion_depth (error 3636), no SEARCH/CYCLE; 5.7 workarounds moved to a legacy section; fixed `PRIMARY` → `PRIMARY KEY`.

## Oracle

CTEs implement sequential logic / reusable code via a named subquery used multiple times. Implemented with the `WITH` clause (ANSI SQL-99, available since Oracle 9.2). Similar to an inline view or temp table; reduces repetition and improves readability.

```sql
-- Syntax
WITH <subquery name> AS (<subquery code>)[...]
SELECT <Select list> FROM <subquery name>;

-- Example: department employee counts
WITH DEPT_COUNT (DEPARTMENT_ID, DEPT_COUNT) AS
(SELECT DEPARTMENT_ID, COUNT(*)
 FROM EMPLOYEES
 GROUP BY DEPARTMENT_ID)
SELECT E.FIRST_NAME ||' '|| E.LAST_NAME AS EMP_NAME,
       D.DEPT_COUNT AS EMP_DEPT_COUNT
FROM EMPLOYEES E JOIN DEPT_COUNT D
USING (DEPARTMENT_ID)
ORDER BY 2;
```

## MySQL

**Aurora MySQL 3 and 8.4 support non-recursive and recursive CTEs** (`WITH`, `WITH RECURSIVE`; verified on 3.13.0 and 8.4.8). The Oracle example converts with only the concatenation change (`||` → `CONCAT`):

```sql
WITH dept_count (department_id, dept_count) AS
  (SELECT department_id, COUNT(*) FROM employees GROUP BY department_id)
SELECT CONCAT(e.first_name, ' ', e.last_name) AS emp_name, d.dept_count AS emp_dept_count
FROM employees e JOIN dept_count d USING (department_id)
ORDER BY 2;
```

### `CONNECT BY` → `WITH RECURSIVE` (verified)

```sql
-- Oracle: SELECT employee, LEVEL-1, SYS_CONNECT_BY_PATH(employee,'/') FROM employees
--         START WITH direct_manager IS NULL CONNECT BY PRIOR employee = direct_manager
WITH RECURSIVE h AS (
  SELECT employee, direct_manager, 0 AS lvl, CAST(employee AS CHAR(1000)) AS path
  FROM employees WHERE direct_manager IS NULL
  UNION ALL
  SELECT c.employee, c.direct_manager, h.lvl + 1, CONCAT(h.path, '/', c.employee)
  FROM employees c JOIN h ON c.direct_manager = h.employee)
SELECT employee, lvl, path FROM h ORDER BY path;
```

- **Column types come from the anchor member.** Without the `CAST(… AS CHAR(1000))`, the path column is `varchar(5)` and the recursive step fails with *Data too long for column 'path'* (error 1406, verified with `STRICT_TRANS_TABLES` set). Under Aurora's default (empty) `sql_mode` there is no error and no warning: the string is silently truncated to the anchor width (`'a-x-x-x'` comes back as `'a'`, verified on 3.13.0 and 8.4.8). Widen every column that grows in the recursive part.
- **Recursion limit:** `cte_max_recursion_depth` = 1000 by default; a deeper or runaway recursion stops with error 3636 (verified). Raise it per session (`SET SESSION cte_max_recursion_depth = 100000`) or bound the recursion with a level column.
- `LIMIT` inside a recursive CTE works (8.0.19+, verified).
- No `SEARCH DEPTH/BREADTH FIRST` or `CYCLE` clauses and no `NOCYCLE`: build an ordering path (as above) for `ORDER SIBLINGS BY`, and stop cycles with `WHERE FIND_IN_SET(c.employee, REPLACE(h.path,'/',',')) = 0`.
- `CONNECT_BY_ROOT` → carry the root column through the recursion; `CONNECT_BY_ISLEAF` → `NOT EXISTS (SELECT 1 FROM employees x WHERE x.direct_manager = h.employee)`.
- CTEs can be used in views and in `INSERT … SELECT`, `UPDATE` and `DELETE` (multi-table forms).

### Legacy: Aurora MySQL 5.7 workarounds
Aurora MySQL 2 (5.7) is past standard support. The derived-table and stored-procedure-loop workarounds from the original playbook are only needed there:

**Non-recursive CTE → derived table** (subquery in `FROM`). Repeat the derived-table definition if multiple instances are needed.

```sql
-- Oracle/ANSI CTE
WITH TopCustomerOrders AS (
  SELECT Customer, COUNT(*) AS NumOrders FROM Orders GROUP BY Customer
)
SELECT TOP 10 * FROM TopCustomerOrders ORDER BY NumOrders DESC;

-- MySQL derived table
SELECT *
FROM ( SELECT Customer, COUNT(*) AS NumOrders
       FROM Orders
       GROUP BY Customer ) AS TopCustomerOrders
ORDER BY NumOrders DESC
LIMIT 10 OFFSET 0;
```

Full derived-table example:

```sql
CREATE TABLE OrderItems(
    OrderID INT NOT NULL, Item VARCHAR(20) NOT NULL,
    Quantity SMALLINT NOT NULL,
    PRIMARY KEY (OrderID, Item));

INSERT INTO OrderItems (OrderID, Item, Quantity)
VALUES (1,'M8 Bolt',100),(2,'M8 Nut',100),(3,'M8 Washer',200),(3,'M6 Washer',100);

SELECT O.OrderID, O.Item, O.Quantity, (O.Quantity / AO.TotalQty) * 100 AS PercentOfOrder
FROM OrderItems AS O
  INNER JOIN
  ( SELECT OrderID, SUM(Quantity) AS TotalQty FROM OrderItems GROUP BY OrderID ) AS AO
  ON O.OrderID = AO.OrderID;
```

**Recursive CTE → loop inside a stored procedure/function.** Recursion is off by default; set `max_sp_recursion_depth >= 1` to enable (not recommended — increases thread stack contention). A `WHILE` loop is preferred.

```sql
CREATE TABLE Employees
( Employee VARCHAR(5) NOT NULL PRIMARY KEY, DirectManager VARCHAR(5) NULL);
INSERT INTO Employees VALUES ('John','Dave'),('Jose','Dave'),('Fred','John'),('Dave',NULL);

CREATE TABLE EmpHierarchy (LVL INT, Employee VARCHAR(5), Manager VARCHAR(5));

CREATE PROCEDURE P()
BEGIN
  DECLARE var_lvl INT;
  DECLARE var_Employee VARCHAR(5);
  SET var_lvl = 0;
  SET var_Employee = (SELECT Employee FROM Employees WHERE DirectManager IS NULL);
  INSERT INTO EmpHierarchy VALUES (var_lvl, var_Employee, NULL);
  WHILE var_lvl <> -1 DO
    INSERT INTO EmpHierarchy (LVL, Employee, Manager)
    SELECT var_lvl + 1, Employee, DirectManager
    FROM Employees
    WHERE DirectManager IN (SELECT Employee FROM EmpHierarchy WHERE LVL = var_lvl);
    IF NOT EXISTS (SELECT * FROM EmpHierarchy WHERE LVL = var_lvl + 1)
      THEN SET var_lvl = -1;
      ELSE SET var_lvl = var_lvl + 1;
    END IF;
  END WHILE;
END;

CALL P();
```

## Conversion notes

| Oracle | Aurora MySQL | Comments |
|---|---|---|
| Non-recursive CTE | `WITH` (native) | 5.7 only: derived table |
| Recursive CTE / `CONNECT BY` | `WITH RECURSIVE` (native) | widen growing columns in the anchor; `cte_max_recursion_depth` |

- On Aurora MySQL 3 / 8.4, convert CTEs and `CONNECT BY` to `WITH [RECURSIVE]`; do not use the 5.7 workarounds.
