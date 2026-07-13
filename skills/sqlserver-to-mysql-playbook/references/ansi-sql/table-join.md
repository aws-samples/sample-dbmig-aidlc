# Table JOIN for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.tablejoin.html

**Conversion category:** Assisted (Four star feature compatibility)
**SCT automation:** Four star automation level

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

ANSI SQL 89 comma syntax supported for inner joins only. `APPLY` / `LATERAL JOIN` are NOT supported.

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
SELECT NULL, NULL, Col1, Col2
FROM T2
WHERE Col1 NOT IN (SELECT Col1 FROM T1);
```

## Conversion notes

| SQL Server | Aurora MySQL | Comments |
|---|---|---|
| `INNER JOIN` with `ON` or commas | Supported | |
| `OUTER JOIN` with `ON` clause | Supported | |
| `OUTER JOIN` with commas | Not supported | Requires T-SQL rewrite post 2008 R2. |
| `CROSS JOIN` or commas | Supported | |
| `CROSS APPLY` / `OUTER APPLY` | Not supported | Rewrite required. |
| `FULL OUTER JOIN` | Not supported | Rewrite using `LEFT JOIN` + `UNION ALL`. |
| Not supported | `NATURAL JOIN` | Not recommended (breaks if table structure changes). |
| Not supported | `STRAIGHT_JOIN` | |
| Not supported | `USING` clause | |
