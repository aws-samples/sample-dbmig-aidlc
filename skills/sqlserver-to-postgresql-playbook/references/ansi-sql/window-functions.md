# Window Functions (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.windowfunctions.html

**Conversion category:** Automatic (Five-star compatibility, five-star automation)
**SCT automation:** N/A. No key differences (but returned data types may differ and require application changes).

## SQL Server

Window functions use an `OVER` clause to define the window/frame. Supported:
- Ranking: `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `NTILE`.
- Aggregate: `AVG`, `MIN`, `MAX`, `SUM`, `COUNT`, `COUNT_BIG`, `VAR`, `STDEV`, `STDEVP`, `STRING_AGG`, `GROUPING`, `GROUPING_ID`, `VARP`, `CHECKSUM_AGG`.
- Analytic: `LAG`, `LEAD`, `FIRST_VALUE`, `LAST_VALUE`, `PERCENT_RANK`, `PERCENTILE_CONT`, `PERCENTILE_DISC`, `CUME_DIST`.
- Other: `NEXT_VALUE_FOR`.

Syntax:
```sql
<Function()>
OVER
(
[ <PARTITION BY clause> ]
[ <ORDER BY clause> ]
[ <ROW or RANGE clause> ]
)
```

Examples:
```sql
-- Ranking
SELECT Item, Quantity,
RANK() OVER(ORDER BY Quantity) AS QtyRank
FROM OrderItems;

-- Partitioned aggregate (no GROUP BY)
SELECT Item, Quantity, OrderID,
SUM(Quantity) OVER (PARTITION BY OrderID) AS TotalOrderQty
FROM OrderItems;

-- Analytic LEAD
SELECT Item, Quantity, OrderID,
  LEAD(Quantity) OVER (PARTITION BY OrderID ORDER BY Quantity) AS NextQtyOrder
FROM OrderItems;
```

## PostgreSQL

ANSI analytic functions are called window functions; same core functionality. Two main types: aggregate and ranking.

| Function type | Related functions |
|---|---|
| Aggregate | `avg`, `count`, `max`, `min`, `sum`, `string_agg` |
| Ranking | `row_number`, `rank`, `dense_rank`, `percent_rank`, `cume_dist`, `ntile`, `lag`, `lead`, `first_value`, `last_value`, `nth_value` |

Returned data types / compatibility:

| Window function | Returned data type | Compatible syntax |
|---|---|---|
| Count | bigint | Yes |
| Max | numeric, string, date/time, network or enum | Yes |
| Min | numeric, string, date/time, network or enum | Yes |
| Avg | numeric, double, otherwise arg type | Yes |
| Sum | bigint, otherwise arg type | Yes |
| rank() | bigint | Yes |
| row_number() | bigint | Yes |
| dense_rank() | bigint | Yes |
| percent_rank() | double | Yes |
| cume_dist() | double | Yes |
| ntile() | integer | Yes |
| lag() | Same type as value | Yes |
| lead() | Same type as value | Yes |
| first_value() | Same type as value | Yes |
| last_value() | Same type as value | Yes |

Examples:
```sql
-- rank() with partition
SELECT department_id, last_name, salary, commission_pct,
RANK() OVER (PARTITION BY department_id
ORDER BY salary DESC, commission_pct) "Rank"
FROM employees WHERE department_id = 80;

-- Ranking
SELECT Item, Quantity, RANK()
  OVER(ORDER BY Quantity) AS QtyRank
FROM OrderItems;

-- Partitioned aggregate (no GROUP BY)
SELECT Item, Quantity, OrderID, SUM(Quantity)
  OVER (PARTITION BY OrderID) AS TotalOrderQty
FROM OrderItems;

-- Analytic LEAD
SELECT Item, Quantity, OrderID, LEAD(Quantity)
  OVER (PARTITION BY OrderID ORDER BY Quantity) AS NextQtyOrder
FROM OrderItems;
```

## Conversion notes
- Syntax is highly compatible; most window functions migrate unchanged.
- Returned data types may differ between SQL Server and PostgreSQL (e.g., numeric formatting), which can require application changes — examine each function by type and verify output.
- SQL Server-only functions without direct PostgreSQL window equivalents: `CHECKSUM_AGG`, `GROUPING_ID`, `PERCENTILE_CONT`, `PERCENTILE_DISC`, `NEXT_VALUE_FOR`. PostgreSQL adds `nth_value`.
