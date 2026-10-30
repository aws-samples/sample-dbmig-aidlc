# Window Functions for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.windowfunctions.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** No automation

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Window functions are native on 3 / 8.4 (verified); listed the remaining gaps (PERCENTILE_*, IGNORE NULLS, DISTINCT aggregates, RANGE INTERVAL rule); 5.7 workarounds marked legacy.

**Key differences:** On Aurora MySQL 3 / 8.4, window functions and `OVER (PARTITION BY … ORDER BY …)` are native (verified); convert directly and handle the gaps listed under MySQL. *(Corrected: the playbook's "rewrite to alternative SQL" applied to Aurora MySQL 5.7 only.)* The conversion category above is the playbook's 5.7 rating; on 3 / 8.4 most window-function code is Assisted.

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
**Aurora MySQL 3 and 8.4 support window functions** with SQL Server–compatible syntax (verified on 3.13.0 and 8.4.8): `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `NTILE`, `PERCENT_RANK`, `CUME_DIST`, `LAG`, `LEAD`, `FIRST_VALUE`, `LAST_VALUE`, `NTH_VALUE`, and aggregates with `OVER (PARTITION BY … ORDER BY … ROWS|RANGE …)`, plus named `WINDOW` clauses. Most T-SQL window queries convert unchanged.

Gaps (verified):
- `PERCENTILE_CONT` / `PERCENTILE_DISC` (and `WITHIN GROUP`) are not available — compute with `ROW_NUMBER()`/`COUNT() OVER` and pick the middle rows.
- `IGNORE NULLS` is not supported (error 1235); SQL Server 2022 `IGNORE NULLS` needs a rewrite.
- `STDEV/VAR(DISTINCT …)` are syntax errors; `STRING_AGG … OVER` has no equivalent (`GROUP_CONCAT` is not a window function).
- `RANGE BETWEEN INTERVAL …` frames need exactly one numeric/temporal `ORDER BY` key (error 3587).
- SQL Server's default frame for `ORDER BY` without a frame clause is `RANGE UNBOUNDED PRECEDING`; MySQL uses the same default, so running totals with ties behave the same. Write `ROWS` explicitly when you mean rows.

### Legacy: Aurora MySQL 5.7 workarounds
Correlated-subquery rewrites from the original playbook (only for Aurora MySQL 2):

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
| Window functions and `OVER` clause | Native on Aurora MySQL 3 / 8.4 | Convert directly; rewrite `PERCENTILE_*`, `IGNORE NULLS` and `DISTINCT` window aggregates. 5.7 only: correlated subqueries. |

- 5.7 only: subquery workarounds are functionally equivalent but typically less performant and harder to read.
