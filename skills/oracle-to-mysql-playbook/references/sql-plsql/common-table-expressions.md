# Common Table Expressions (CTE)

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.cte.html

**Conversion category:** Manual (★★ feature compatibility, no automation) — workaround available
**SCT automation:** Action code "Common Table Expressions"

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

**Aurora MySQL 5.7 does NOT support CTEs.** (Amazon RDS for MySQL 8 and MySQL 8.0+ support both non-recursive and recursive CTEs via `WITH`; as of 8.0.19 recursive CTEs support `LIMIT`/`OFFSET`.)

### Workarounds for Aurora MySQL 5.7

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
    PRIMARY (OrderID, Item));

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
| Non-recursive CTE | Derived table | Repeat the derived-table subquery for each instance needed |
| Recursive CTE | Loop inside stored procedure/function | |

- If targeting MySQL 8 / RDS MySQL 8, CTEs are natively supported — no rewrite needed.
- Aurora MySQL 5.7 requires the workarounds above.
