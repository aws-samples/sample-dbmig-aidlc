# Table JOIN (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.tablejoin.html

**Conversion category:** Assisted (Four-star compatibility, four-star automation)
**SCT automation:** N/A. Key differences: `OUTER JOIN` with commas (ANSI 89) not supported; `CROSS APPLY`/`OUTER APPLY` not supported.

## SQL Server

Standard ANSI joins: `CROSS JOIN`, `INNER JOIN ... ON`, `LEFT/RIGHT/FULL OUTER JOIN ... ON`.

`APPLY` operator correlates `<Set A>` with `<Set B>` (subquery/VALUES/table-valued function evaluated per row of A):
- `CROSS APPLY` — like `CROSS JOIN`.
- `OUTER APPLY` — like `LEFT OUTER JOIN` (NULLs when B is empty).

ANSI SQL 89 join (deprecated since 2008R2): comma-separated `FROM` for cross/inner; `*=`/`=*` for outer joins.
```sql
-- ANSI 89 INNER JOIN
SELECT * FROM Table1, Table2
WHERE Table1.Column1 = Table2.Column1

-- ANSI 89 OUTER JOIN (deprecated)
SELECT * FROM Table1, Table2
WHERE Table1.Column1 *= Table2.Column1
```

Syntax:
```sql
-- CROSS JOIN
FROM <Table Source 1> CROSS JOIN <Table Source 2>
-- INNER / OUTER JOIN
FROM <Table Source 1>
  [ { INNER | { { LEFT | RIGHT | FULL } [ OUTER ] } }] JOIN
  <Table Source 2>
  ON <JOIN Predicate>
-- APPLY
FROM <Table Source 1>
  { CROSS | OUTER } APPLY
  <Table Source 2>
```

Examples:
```sql
-- INNER JOIN (and ANSI 89 equivalent)
SELECT * FROM Items AS I
  INNER JOIN OrderItems AS OI ON I.Item = OI.Item;
SELECT * FROM Items AS I, OrderItems AS OI
  WHERE I.Item = OI.Item;

-- LEFT OUTER JOIN: find items never ordered
SELECT I.Item FROM Items AS I
  LEFT OUTER JOIN OrderItems AS OI ON I.Item = OI.Item
WHERE OI.OrderID IS NULL;

-- FULL OUTER JOIN
SELECT * FROM T1
  FULL OUTER JOIN T2 ON T1.Col1 = T2.Col1;
```

## PostgreSQL

Aurora PostgreSQL supports all join types the same way (`CROSS`, `INNER`, `LEFT/RIGHT/FULL OUTER`). It does **not** support `APPLY` — replace with `INNER JOIN LATERAL` / `LEFT JOIN LATERAL`.

Syntax:
```sql
FROM
    <Table Source 1> CROSS JOIN <Table Source 2>
  | <Table Source 1> INNER JOIN <Table Source 2> ON <Join Predicate>
  | <Table Source 1> {LEFT|RIGHT|FULL} [OUTER] JOIN <Table Source 2> ON <Join Predicate>
```

Examples:
```sql
-- INNER JOIN
SELECT * FROM Items AS I
  INNER JOIN OrderItems AS OI ON I.Item = OI.Item;

-- LEFT OUTER JOIN
SELECT Item FROM Items AS I
  LEFT OUTER JOIN OrderItems AS OI ON I.Item = OI.Item
WHERE OI.OrderID IS NULL;

-- FULL OUTER JOIN
SELECT * FROM T1
FULL OUTER JOIN T2 ON T1.Col1 = T2.Col1;
```

## Conversion notes

| SQL Server feature | Aurora PostgreSQL | Comments |
|---|---|---|
| `INNER JOIN` with `ON` or commas | Supported | |
| `OUTER JOIN` with `ON` clause | Supported | |
| `OUTER JOIN` with commas (`*=`/`=*`) | Not supported | Requires T-SQL rewrite (deprecated post-2008R2) |
| `CROSS JOIN` or commas | Supported | |
| `CROSS APPLY` / `OUTER APPLY` | Not supported | Rewrite as `INNER JOIN LATERAL` / `LEFT JOIN LATERAL` |

- Most joins need no rewrite — ANSI 92 `ON`-clause syntax is equivalent.
- ANSI SQL 89 comma joins for INNER work but are discouraged; outer-join `*=`/`=*` syntax is not supported and must be rewritten.
- Convert `CROSS APPLY` → `INNER JOIN LATERAL`, `OUTER APPLY` → `LEFT JOIN LATERAL`.
