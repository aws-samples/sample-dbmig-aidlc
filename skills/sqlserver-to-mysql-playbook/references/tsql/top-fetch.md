# SQL Server TOP and FETCH and MySQL LIMIT for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.topfetch.html

**Conversion category:** Automatic (Four star feature compatibility — syntax rewrite; convert `PERCENT`/`TIES` to subqueries)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): WITH TIES via RANK() (verified), PERCENT workaround fixed to round up (verified), LIMIT with variables, FETCH FIRST unsupported, UPDATE/DELETE TOP, LIMIT in IN-subqueries (1235).

## SQL Server

Two ways to limit/page results: legacy `TOP`, and ANSI `OFFSET…FETCH` (since SQL Server 2012).

### TOP

`TOP (n)` in the SELECT list limits rows per `ORDER BY` (non-deterministic without ORDER BY). Modifiers: `TOP (n) PERCENT` (1–100% of rows), `TOP (n) WITH TIES` (include rows tied with the last row's ordering value).

```sql
SELECT TOP (<Limit Expression>) [PERCENT] [ WITH TIES ] <Select Expressions List>
FROM...
```

### OFFSET… FETCH

Part of the `ORDER BY` clause (cannot be used without it):

```sql
ORDER BY <Ordering Expression> [ ASC | DESC ] [ ,...n ]
OFFSET <Offset Expression> { ROW | ROWS }
[FETCH { FIRST | NEXT } <Page Size Expression> { ROW | ROWS } ONLY ]
```

### Examples

```sql
-- top 3 by quantity
SELECT TOP (3) * FROM OrderItems ORDER BY Quantity DESC;

SELECT * FROM OrderItems
ORDER BY Quantity DESC
OFFSET 0 ROWS FETCH NEXT 3 ROWS ONLY;

-- with ties
SELECT TOP (3) WITH TIES * FROM OrderItems ORDER BY Quantity DESC;

-- top 50 percent
SELECT TOP (50) PERCENT * FROM OrderItems ORDER BY Quantity DESC;
```

## MySQL

Aurora MySQL uses `LIMIT… OFFSET` (non-ANSI but widely used). `LIMIT` doesn't require `ORDER BY` (non-deterministic without it). `OFFSET` is zero-based.

### Examples

```sql
-- top 3 by quantity
SELECT * FROM OrderItems
ORDER BY Quantity DESC
LIMIT 3 OFFSET 0;

-- WITH TIES workaround: union the tied rows
SELECT *
FROM (
    SELECT * FROM OrderItems ORDER BY Quantity DESC LIMIT 3 OFFSET 0
) AS X
UNION
SELECT * FROM OrderItems
WHERE Quantity = (
    SELECT Quantity FROM OrderItems ORDER BY Quantity DESC LIMIT 1 OFFSET 2
)
ORDER BY Quantity DESC;

-- PERCENT workaround: compute the row count in a procedure
CREATE PROCEDURE P(Percent INT)
BEGIN
DECLARE N INT;
SELECT CEIL(COUNT(*) * Percent / 100) FROM OrderItems INTO N;   -- CEIL: SQL Server rounds PERCENT up; without it 10% of 4 rows gives 0 (verified)
SELECT * FROM OrderItems
ORDER BY Quantity DESC
LIMIT N OFFSET 0;
END
CALL P(50);
```

## Conversion notes

- `TOP (n)` → `LIMIT n`; `OFFSET…FETCH` → `LIMIT… OFFSET`. AWS SCT auto-converts these.
- `WITH TIES` and `PERCENT` are **not** supported — require manual workarounds.
  - `PERCENT`: compute row count first, then `LIMIT` a fixed number (two table accesses). Consider switching to a fixed number.
  - `WITH TIES`: *(updated)* on Aurora MySQL 3 / 8.4 use a window function — `SELECT * FROM (SELECT t.*, RANK() OVER (ORDER BY Quantity DESC) AS rk FROM OrderItems t) x WHERE rk <= 3` (verified) — instead of the three-access UNION workaround.
- `LIMIT` accepts routine parameters and local variables inside procedures (verified `LIMIT n`), but not user variables or expressions; compute the value into a local variable first. Outside routines use a prepared statement (`LIMIT ?`).
- `OFFSET n ROWS FETCH NEXT m ROWS ONLY` → `LIMIT m OFFSET n`; `FETCH FIRST` syntax does not exist in MySQL (verified).
- `UPDATE TOP (n)` / `DELETE TOP (n)` → single-table `… ORDER BY … LIMIT n`; multi-table forms reject `LIMIT` (error 1221, verified).
- `LIMIT` inside an `IN`/`ANY`/`ALL` subquery is not supported (error 1235, verified) — wrap it in a derived table.

| SQL Server | Aurora MySQL | Comments |
|---|---|---|
| `TOP (n)` | `LIMIT n` | |
| `TOP (n) WITH TIES` | Not supported | `RANK() OVER (…) <= n` in a derived table (verified) |
| `TOP (n) PERCENT` | Not supported | computed count with `CEIL` |
| `OFFSET… FETCH` | `LIMIT… OFFSET` | |
