# TOP and FETCH

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.topfetch.html

**Conversion category:** Automatic (four-star feature compatibility, four-star automation)
**SCT automation:** Four-star automation level; SCT action code index: TOP and FETCH

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): WITH TIES is native since PG 13 (verified) — the UNION workaround is obsolete; OFFSET…FETCH converts unchanged; PERCENT workaround fixed to round up like SQL Server; UPDATE/DELETE TOP rewrite added.

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

Aurora PostgreSQL supports both the ANSI `OFFSET … FETCH { FIRST | NEXT } n ROWS { ONLY | WITH TIES }` (`WITH TIES` since PG 13) and `LIMIT … OFFSET` (non-ANSI but widely used). `OFFSET … FETCH` from SQL Server converts unchanged. `LIMIT` limits rows (no ORDER BY required, though recommended). `OFFSET` is zero-based; `OFFSET 0`/NULL = no offset. SCT auto-converts `TOP(n)` and `FETCH…OFFSET` except `WITH TIES` and `PERCENT`.

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

**WITH TIES — native since PG 13** (verified on Aurora PostgreSQL 18.6; returns the 4 rows that tie on the 3rd value, like SQL Server):

```sql
SELECT * FROM OrderItems ORDER BY Quantity DESC FETCH FIRST 3 ROWS WITH TIES;
```

`WITH TIES` requires `ORDER BY` (error 42601 otherwise), as in SQL Server.

Original PG 10 workaround, no longer needed:

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

**PERCENT workaround** (compute count × pct). SQL Server rounds the row count **up**, so use `ceil`; the original `COUNT(*)*$1/100` uses integer division and returns too few rows (5 rows at 50 % → 2 instead of 3):

```sql
CREATE OR REPLACE FUNCTION getOrdersPct(int) RETURNS SETOF OrderItems AS $$
SELECT * FROM OrderItems
ORDER BY Quantity DESC
FETCH FIRST (SELECT ceil(count(*) * $1 / 100.0)::int FROM OrderItems) ROWS ONLY;
$$ LANGUAGE SQL;

SELECT * from getOrdersPct(50);
```

## Summary

| SQL Server | Aurora PostgreSQL | Comments |
|---|---|---|
| `TOP (n)` | `LIMIT n` | |
| `TOP (n) WITH TIES` | `FETCH FIRST n ROWS WITH TIES` | PG 13+ |
| `TOP (n) PERCENT` | Not supported | See workaround (`ceil`) |
| `OFFSET… FETCH` | `OFFSET… FETCH` (or `LIMIT… OFFSET`) | unchanged |
| `UPDATE/DELETE TOP (n)` | Not supported | `WHERE ctid = ANY (ARRAY(SELECT ctid FROM t WHERE … LIMIT n))` or `WHERE pk IN (SELECT pk … LIMIT n)` |

## Conversion notes
- `TOP (n)` → `LIMIT n`; `OFFSET ... FETCH NEXT n ROWS ONLY` → `LIMIT n OFFSET m`. Auto-converted by SCT.
- `WITH TIES` → native `FETCH FIRST n ROWS WITH TIES` (PG 13+); the UNION workaround is obsolete.
- `TOP (@n)` with a variable → `LIMIT v_n` / `FETCH FIRST v_n ROWS ONLY` in PL/pgSQL (parameters are allowed).
- `DELETE TOP (n) FROM t WHERE …` (batch deletes) → `DELETE FROM t WHERE pk IN (SELECT pk FROM t WHERE … LIMIT n)`; PostgreSQL has no `LIMIT` on `UPDATE`/`DELETE`.
- `PERCENT` has no native equivalent — compute `ceil(count(*) * pct / 100.0)` first (accesses the table twice); consider switching to a fixed count.
- Always pair LIMIT/OFFSET with a deterministic ORDER BY.
