# GROUP BY for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.groupby.html

**Conversion category:** Assisted (Four star feature compatibility)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): WITH ROLLUP + ORDER BY and GROUPING() work in MySQL 8 (corrected, verified); STRING_AGG → GROUP_CONCAT with truncation; ONLY_FULL_GROUP_BY not in the Aurora default sql_mode.

**Key differences:** Basic syntax compatible. Advanced options such as `ALL`, `CUBE`, `GROUPING SETS` require rewrites to use multiple queries with `UNION`.

## SQL Server

`GROUP BY` groups rows for aggregate functions. Supports `CUBE`, `ROLLUP`, `GROUPING SETS`, and legacy non-ANSI `WITH CUBE`/`WITH ROLLUP` and `GROUP BY ALL` (deprecated after 2008 R2).

Aggregate functions: `AVG`, `CHECKSUM_AGG`, `COUNT`, `COUNT_BIG`, `GROUPING`, `GROUPING_ID`, `STDEV`, `STDEVP`, `STRING_AGG`, `SUM`, `MIN`, `MAX`, `VAR`, `VARP`.

### Syntax
```sql
GROUP BY
[ROLLUP | CUBE]
<Column Expression> ...n
[GROUPING SETS (<Grouping Set>)...n
```

### Examples

`WITH ROLLUP`:
```sql
SELECT Customer, OrderDate, COUNT(*) AS NumOrders
FROM Orders AS O
GROUP BY Customer, OrderDate
WITH ROLLUP
```

`GROUPING SETS` (equivalent to CUBE):
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

## MySQL

Aurora MySQL supports only basic ANSI `GROUP BY` plus the non-ANSI `WITH ROLLUP`. No `GROUPING SETS`, `CUBE`, or ANSI `ROLLUP`/`CUBE`.

Aggregate functions (wider than SQL Server): `AVG`, `BIT_AND`, `BIT_OR`, `BIT_XOR`, `COUNT`, `GROUP_CONCAT`, `JSON_ARRAYAGG`, `JSON_OBJECTAGG`, `MAX`, `MIN`, `STD`, `STDDEV`, `STDDEV_POP`, `STDDEV_SAMP`, `SUM`, `VAR_POP`, `VAR_SAMP`, `VARIANCE`.

Limitations:
- *(corrected for MySQL 8)* `WITH ROLLUP` **and** `ORDER BY` work together (8.0.12+), and the **`GROUPING()`** function distinguishes super-aggregate NULLs (8.0.1+) — verified on 3.13 and 8.4.8. No `GROUPING_ID` — combine `GROUPING(a) * 2 + GROUPING(b)`.
- `ROLLUP` super-aggregate rows can't be referenced in `WHERE` or join conditions (filter in `HAVING` or an outer query).
- Functional-dependency detection allows non-aggregate columns not in `GROUP BY` (ANSI feature T301). Turn on `ONLY_FULL_GROUP_BY` SQL mode to restrict.

### Syntax
```sql
SELECT <Select List>
FROM <Table Source>
WHERE <Row Filter>
GROUP BY <Column Name> | <Expression> | <Position>
    [ASC | DESC], ...
    [WITH ROLLUP]]
```

### Examples

Rewrite `WITH CUBE` using `UNION ALL`:
```sql
SELECT Customer, OrderDate, COUNT(*) AS NumOrders
FROM Orders AS O
GROUP BY Customer, OrderDate
WITH ROLLUP
UNION ALL
SELECT NULL, OrderDate, COUNT(*) AS NumOrders
FROM Orders AS O
GROUP BY OrderDate
```

Rewrite `GROUP BY ALL` using `UNION ALL`:
```sql
SELECT Customer, OrderDate, COUNT(*) AS NumOrders
FROM Orders AS O
WHERE OrderDate <= '20180503'
GROUP BY Customer, OrderDate
UNION ALL
SELECT DISTINCT Customer, OrderDate, NULL
FROM Orders AS O
WHERE OrderDate > '20180503';
```

## Conversion notes

| SQL Server feature | Aurora MySQL feature | Comments |
|---|---|---|
| `MAX`, `MIN`, `AVG`, `COUNT`, `COUNT_BIG` | `MAX`, `MIN`, `AVG`, `COUNT` | `COUNT` returns `BIGINT`, compatible with `COUNT`/`COUNT_BIG`. |
| `CHECKSUM_AGG` | N/A | Use a loop. |
| `GROUPING`, `GROUPING_ID` | `GROUPING()` (8.0+) | `GROUPING_ID` → arithmetic over `GROUPING()` calls. |
| `STDEV`, `STDEVP`, `VAR`, `VARP` | `STDDEV`, `STDDEV_POP`, `VARIANCE`, `VAR_POP` | Rewrite keywords only. |
| `STRING_AGG(x, ',') WITHIN GROUP (ORDER BY y)` | `GROUP_CONCAT(x ORDER BY y SEPARATOR ',')` | Rewrite syntax (`STRING_AGG` does not exist, verified). Output is truncated at `group_concat_max_len` (1024 bytes by default) — raise it. |
| `WITH ROLLUP` | `WITH ROLLUP` | Compatible. |
| `WITH CUBE` | N/A | Rewrite using `UNION ALL`. |
| `ANSI CUBE` / `ROLLUP` | N/A | Rewrite using `WITH ROLLUP` + `UNION ALL`. |
| `GROUPING SETS` | N/A | Rewrite using `UNION ALL`. |
| N/A | Non-aggregate columns in `HAVING`/`SELECT`/`ORDER BY` | Aurora's default `sql_mode` does **not** include `ONLY_FULL_GROUP_BY` (verified), so `SELECT a, b … GROUP BY a` runs and returns an arbitrary `b`. SQL Server rejects it; enable `ONLY_FULL_GROUP_BY` to catch conversion mistakes. |
