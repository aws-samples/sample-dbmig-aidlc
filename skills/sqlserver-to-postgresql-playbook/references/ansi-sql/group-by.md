# GROUP BY (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.groupby.html

**Conversion category:** Automatic (Five-star compatibility, five-star automation)
**SCT automation:** N/A. No key differences flagged, though `WITH CUBE`/`WITH ROLLUP`/`GROUP BY ALL` legacy syntax requires rewrite.

## SQL Server

`GROUP BY` groups rows for aggregate functions. Supports `ROLLUP`, `CUBE`, and `GROUPING SETS`.

ANSI syntax:
```sql
GROUP BY
[ROLLUP | CUBE]
<Column Expression> ...n
[GROUPING SETS (<Grouping Set>)...n
```

Legacy (backward-compatible, non-ANSI) syntax:
```sql
GROUP BY
  [ ALL ] <Column Expression> ...n
  [ WITH CUBE | ROLLUP ]
```

Aggregate functions: `AVG`, `CHECKSUM_AGG`, `COUNT`, `COUNT_BIG`, `GROUPING`, `GROUPING_ID`, `STDEV`, `STDEVP`, `STRING_AGG`, `SUM`, `MIN`, `MAX`, `VAR`, `VARP`.

Legacy `WITH ROLLUP`:
```sql
SELECT Customer, OrderDate, COUNT(*) AS NumOrders
FROM Orders AS O
GROUP BY Customer, OrderDate
WITH ROLLUP
```

Legacy `WITH CUBE`:
```sql
SELECT Customer, OrderDate, COUNT(*) AS NumOrders
FROM Orders AS O
GROUP BY Customer, OrderDate
WITH CUBE
```

Legacy `GROUP BY ALL` (creates empty groups for rows failing WHERE):
```sql
SELECT Customer, OrderDate, COUNT(*) AS NumOrders
FROM Orders AS O
WHERE OrderDate <= '20180503'
GROUP BY ALL Customer, OrderDate
```

ANSI `GROUPING SETS`:
```sql
SELECT Customer, OrderDate, COUNT(*) AS NumOrders
FROM Orders AS O
GROUP BY GROUPING SETS (
  (Customer, OrderDate),
  (Customer),
  (OrderDate),
  ()
)
```

## PostgreSQL

Aurora PostgreSQL supports basic ANSI `GROUP BY` plus `GROUPING SETS`, `CUBE`, and `ROLLUP`. No `WITH` clause — the columns go after the `ROLLUP`/`CUBE` keyword.

Syntax:
```sql
SELECT <Select List>
FROM <Table Source>
WHERE <Row Filter>
GROUP BY
  [ROLLUP | CUBE | GROUPING SETS]
<Column Name> | <Expression> | <Position>
```

ROLLUP / CUBE / GROUPING SETS:
```sql
SELECT Customer, OrderDate, COUNT(*) AS NumOrders
FROM Orders AS O
GROUP BY ROLLUP (Customer, OrderDate);

SELECT Customer, OrderDate, COUNT(*) AS NumOrders
FROM Orders AS O
GROUP BY CUBE (Customer, OrderDate);

SELECT Customer, OrderDate, COUNT(*) AS NumOrders
FROM Orders AS O
GROUP BY GROUPING SETS (
  (Customer, OrderDate),
  (Customer),
  (OrderDate),
  ()
);
```

Rewriting `GROUP BY ALL` (no equivalent — use UNION ALL to add empty groups):
```sql
SELECT Customer, OrderDate, COUNT(*) AS NumOrders
FROM Orders AS O
WHERE OrderDate <= '20180503'
GROUP BY Customer, OrderDate
UNION ALL -- Add the empty groups
SELECT DISTINCT Customer, OrderDate, 0
FROM Orders AS O
WHERE OrderDate > '20180503';
```

## Conversion notes

| SQL Server | Aurora PostgreSQL | Comments |
|---|---|---|
| `MAX`, `MIN`, `AVG`, `COUNT`, `COUNT_BIG` | `MAX`, `MIN`, `AVG`, `COUNT` | PostgreSQL `COUNT` returns `BIGINT`, compatible with both `COUNT`/`COUNT_BIG` |
| `CHECKSUM_AGG` | N/A | Use a loop to calculate checksums |
| `GROUPING`, `GROUPING_ID` | `GROUPING` | Avoid NULL groups ambiguous with super aggregates |
| `STDEV`, `STDEVP`, `VAR`, `VARP` | `STDDEV`, `STDDEV_POP`, `VARIANCE`, `VAR_POP` | Rewrite keyword names only |
| `STRING_AGG` | `STRING_AGG` | |
| `WITH ROLLUP` | `ROLLUP` | Remove `WITH`; move columns after `ROLLUP` |
| `WITH CUBE` | `CUBE` | Remove `WITH`; move columns after `CUBE` |
| `GROUPING SETS` | `GROUPING SETS` | |

- All `GROUP BY` functionality exists except `GROUP BY ALL` — rewrite with `UNION ALL`.
- Move column names to after the `CUBE`/`ROLLUP` keyword and drop the `WITH` prefix.
- Rename statistical aggregates (`STDEV`→`STDDEV`, etc.).
- `CHECKSUM_AGG` has no equivalent.
