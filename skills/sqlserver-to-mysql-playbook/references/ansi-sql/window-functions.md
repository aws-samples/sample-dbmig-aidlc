# Window Functions for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.windowfunctions.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** No automation

**Key differences:** Rewrite window functions to use alternative SQL syntax. (Aurora MySQL 5.7 lacks window functions; RDS for MySQL 8 supports them.)

## SQL Server

Window functions use an `OVER` clause. Categories:

| Category | Examples |
|---|---|
| Ranking | `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `NTILE` |
| Aggregate | `AVG`, `MIN`, `MAX`, `SUM`, `COUNT`, `COUNT_BIG`, `VAR`, `STDEV`, `STDEVP`, `STRING_AGG`, `GROUPING`, `GROUPING_ID`, `VARP`, `CHECKSUM_AGG` |
| Analytic | `LAG`, `LEAD`, `FIRST_VALUE`, `LAST_VALUE`, `PERCENT_RANK`, `PERCENTILE_CONT`, `PERCENTILE_DISC`, `CUME_DIST` |
| Other | `NEXT_VALUE_FOR` |

### Syntax
```sql
<Function()>
OVER
(
[ <PARTITION BY clause> ]
[ <ORDER BY clause> ]
[ <ROW or RANGE clause> ]
)
```

### Examples

Ranking:
```sql
SELECT Item, Quantity,
    RANK() OVER(ORDER BY Quantity) AS QtyRank
FROM OrderItems;
```

Partitioned aggregate:
```sql
SELECT Item, Quantity, OrderID,
    SUM(Quantity) OVER (PARTITION BY OrderID) AS TotalOrderQty
FROM OrderItems;
```

Analytic LEAD:
```sql
SELECT Item, Quantity, OrderID,
    LEAD(Quantity) OVER (PARTITION BY OrderID ORDER BY Quantity) AS NextQtyOrder
FROM OrderItems;
```

## MySQL

Aurora MySQL 5.7 does NOT support window functions. (RDS for MySQL 8 supports them with ANSI-compliant, T-SQL-compatible syntax.) Workaround: rewrite using correlated subqueries.

### Examples

Ranking workaround:
```sql
SELECT Item, Quantity,
(
    SELECT COUNT(*)
    FROM OrderItems AS OI2
    WHERE OI.Quantity > OI2.Quantity) + 1
    AS QtyRank
FROM OrderItems AS OI;
```

Partitioned aggregate workaround:
```sql
SELECT Item, Quantity, OrderID,
(
    SELECT SUM(Quantity)
    FROM OrderItems AS OI2
    WHERE OI2.OrderID = OI.OrderID)
    AS TotalOrderQty
FROM OrderItems AS OI;
```

`LEAD` workaround:
```sql
SELECT Item, Quantity, OrderID,
(
    SELECT Quantity
    FROM OrderItems AS OI2
    WHERE OI.OrderID = OI2.OrderID
        AND OI2.Quantity > OI.Quantity
    ORDER BY Quantity
        LIMIT 1
    )
    AS NextQtyOrder
FROM OrderItems AS OI
```

## Conversion notes

| SQL Server | Aurora MySQL | Comments |
|---|---|---|
| Window functions and `OVER` clause | Not supported yet (5.7) | Convert to traditional SQL such as correlated subqueries. |

- Archive original window-function code for potential reuse when upgrading to MySQL 8.
- Subquery workarounds are functionally equivalent but typically less performant and harder to read.
