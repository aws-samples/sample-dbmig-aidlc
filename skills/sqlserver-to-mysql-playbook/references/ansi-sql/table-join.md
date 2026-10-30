# Table JOIN for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.tablejoin.html

**Conversion category:** Assisted (Four star feature compatibility)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): LATERAL is supported on 3 / 8.4 (corrected, verified) as the APPLY replacement; FULL OUTER JOIN still unsupported (verified); fixed the NOT IN null trap in the rewrite.

**Key differences:** Basic syntax compatible. `FULL OUTER`, `APPLY`, and ANSI SQL 89 outer joins need rewrites.

## SQL Server

Standard ANSI joins: `CROSS JOIN`, `INNER JOIN`, `LEFT OUTER JOIN`, `RIGHT OUTER JOIN`, `FULL OUTER JOIN`.

`APPLY` operator (correlated, not a standard join):
- `CROSS APPLY` — like `CROSS JOIN` per row; `<Set B>` can reference current `<Set A>` row.
- `OUTER APPLY` — like `LEFT OUTER JOIN`; returns `<Set A>` rows even when `<Set B>` is empty.

ANSI SQL 89 syntax (deprecated after 2008 R2): comma-separated tables in `FROM`, outer joins with `*=` / `=*`.

### Syntax
```sql
FROM <Table Source 1>
    [ { INNER | { { LEFT | RIGHT | FULL } [ OUTER ] } }] JOIN
    <Table Source 2>
    ON <JOIN Predicate>
```

### Examples

INNER JOIN:
```sql
SELECT *
FROM Items AS I
    INNER JOIN
    OrderItems AS OI
    ON I.Item = OI.Item;
```

FULL OUTER JOIN:
```sql
SELECT *
FROM T1
    FULL OUTER JOIN
    T2
    ON T1.Col1 = T2.Col1;
```

## MySQL

Aurora MySQL supports `CROSS JOIN`, `INNER JOIN`, `LEFT OUTER JOIN`, `RIGHT OUTER JOIN` — but NOT `FULL OUTER JOIN`.

Additional join types not in SQL Server:
- `NATURAL [INNER | LEFT OUTER | RIGHT OUTER] JOIN` — implicit predicate on all same-named columns.
- `STRAIGHT_JOIN` — forces left set read first (optimizer hint).
- `USING (column list)` clause as alternative to `ON`.

ANSI SQL 89 comma syntax supported for inner joins only. *(corrected)* **`LATERAL` derived tables are supported** on Aurora MySQL 3 / 8.4 (MySQL 8.0.14+): `CROSS APPLY (…)` → `JOIN LATERAL (…) AS x ON TRUE`, `OUTER APPLY (…)` → `LEFT JOIN LATERAL (…) AS x ON TRUE` (verified). `FULL OUTER JOIN` is still a syntax error (verified).

### Syntax
```sql
FROM
    <Table Source 1> CROSS JOIN <Table Source 2>
    | <Table Source 1> INNER JOIN <Table Source 2>
        ON <Join Predicate> | USING (Equality Comparison Column List)
    | <Table Source 1> {LEFT|RIGHT} [OUTER] JOIN <Table Source 2>
        ON <Join Predicate> | USING (Equality Comparison Column List)
    | <Table Source 1> NATURAL [INNER | {LEFT|RIGHT} [OUTER]] JOIN <Table Source 2>
    | <Table Source 1> STRAIGHT_JOIN <Table Source 2>
        ON <Join Predicate>
```

### Examples

`USING` clause (equivalent to `ON Table1.Column1 = Table2.Column1`):
```sql
FROM Table1
    INNER JOIN
    Table2
    USING (Column1);
```

Rewrite for FULL OUTER JOIN using `UNION ALL`:
```sql
SELECT *
FROM T1
    LEFT OUTER JOIN
    T2
    ON T1.Col1 = T2.Col1
UNION ALL
SELECT NULL, NULL, T2.Col1, T2.Col2
FROM T2
WHERE NOT EXISTS (SELECT 1 FROM T1 WHERE T1.Col1 = T2.Col1);
-- NOT EXISTS instead of the original NOT IN: NOT IN returns no rows if T1.Col1 contains a NULL
```

## Conversion notes

| SQL Server | Aurora MySQL | Comments |
|---|---|---|
| `INNER JOIN` with `ON` or commas | Supported | |
| `OUTER JOIN` with `ON` clause | Supported | |
| `OUTER JOIN` with commas | Not supported | Requires T-SQL rewrite post 2008 R2. |
| `CROSS JOIN` or commas | Supported | |
| `CROSS APPLY` / `OUTER APPLY` | `JOIN LATERAL` / `LEFT JOIN LATERAL … ON TRUE` | MySQL 8.0.14+ (verified). Applying a table-valued function has no equivalent (MySQL has no TVFs). |
| `FULL OUTER JOIN` | Not supported | Rewrite using `LEFT JOIN` + `UNION ALL`. |
| Not supported | `NATURAL JOIN` | Not recommended (breaks if table structure changes). |
| Not supported | `STRAIGHT_JOIN` | |
| Not supported | `USING` clause | |
