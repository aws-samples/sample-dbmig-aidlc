# TOP and FETCH

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.topfetch.html

**Conversion category:** Automatic (four-star feature compatibility, four-star automation)
**SCT automation:** Four-star automation level; SCT action code index: TOP and FETCH

## SQL Server

Two options for limiting/paging: `TOP` (legacy proprietary) and ANSI `OFFSET`/`FETCH` (SQL Server 2012+, recommended).

**TOP (n)** in the SELECT list, ordered by ORDER BY. Without ORDER BY it is non-deterministic. Modifiers:
- `TOP (n) PERCENT` — percentage (1–100) instead of fixed count.
- `TOP (n) WITH TIES` — include extra rows tying with the last row's ordering value (else non-deterministic for the boundary).

Syntax:

```sql
ORDER BY <Ordering Expression> [ ASC | DESC ] [ ,...n ]
OFFSET <Offset Expression> { ROW | ROWS }
[FETCH { FIRST | NEXT } <Page Size Expression> { ROW | ROWS } ONLY ]
```

Examples:

```sql
-- Using TOP
SELECT TOP (3) * FROM OrderItems ORDER BY Quantity DESC;

-- Using FETCH/OFFSET
SELECT * FROM OrderItems ORDER BY Quantity DESC
OFFSET 0 ROWS FETCH NEXT 3 ROWS ONLY;

-- WITH TIES
SELECT TOP (3) WITH TIES * FROM OrderItems ORDER BY Quantity DESC;

-- PERCENT
SELECT TOP (50) PERCENT * FROM OrderItems ORDER BY Quantity DESC;
```

## PostgreSQL

Aurora PostgreSQL uses `LIMIT … OFFSET` (non-ANSI but widely used). `LIMIT` limits rows (no ORDER BY required, though recommended). `OFFSET` is zero-based; `OFFSET 0`/NULL = no offset. SCT auto-converts `TOP(n)` and `FETCH…OFFSET` except `WITH TIES` and `PERCENT`.

Syntax:

```sql
SELECT select_list
  FROM table_expression
  [ ORDER BY ... ]
  [ LIMIT { number | ALL } ] [ OFFSET number ]
```

Top 3:

```sql
SELECT * FROM OrderItems ORDER BY Quantity DESC LIMIT 3 OFFSET 0;
```

**WITH TIES workaround** (extra query for rows tying the last value):

```sql
SELECT *
FROM ( SELECT * FROM OrderItems ORDER BY Quantity DESC LIMIT 3 OFFSET 0 ) AS X
UNION
SELECT * FROM OrderItems
WHERE Quantity = (
  SELECT Quantity FROM OrderItems ORDER BY Quantity DESC LIMIT 1 OFFSET 2
)
ORDER BY Quantity DESC
```

**PERCENT workaround** (compute count × pct):

```sql
CREATE or replace FUNCTION getOrdersPct(int) RETURNS SETOF OrderItems AS $$
SELECT * FROM OrderItems
ORDER BY Quantity desc LIMIT (SELECT COUNT(*)*$1/100 FROM OrderItems) OFFSET 0;
$$ LANGUAGE SQL;

SELECT * from getOrdersPct(50);
```

## Summary

| SQL Server | Aurora PostgreSQL | Comments |
|---|---|---|
| `TOP (n)` | `LIMIT n` | |
| `TOP (n) WITH TIES` | Not supported | See workaround |
| `TOP (n) PERCENT` | Not supported | See workaround |
| `OFFSET… FETCH` | `LIMIT… OFFSET` | |

## Conversion notes
- `TOP (n)` → `LIMIT n`; `OFFSET ... FETCH NEXT n ROWS ONLY` → `LIMIT n OFFSET m`. Auto-converted by SCT.
- `WITH TIES` has no native equivalent — add a UNION query for tying rows, or (recommended) add a tie-breaker column to ORDER BY.
- `PERCENT` has no native equivalent — compute the row count first (accesses the table twice); consider switching to a fixed count.
- Always pair LIMIT/OFFSET with a deterministic ORDER BY.
