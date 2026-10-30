# DELETE and UPDATE FROM

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.delete.html

**Conversion category:** Assisted (three-star feature compatibility, three-star automation)
**SCT automation:** Three-star automation level; N/A action code

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): `DELETE … USING` exists (corrected), fixed the `UPDATE … FROM` example that updated every row, `NOT EXISTS` over `NOT IN`, PG 18 `RETURNING old/new` (verified), `TOP` in DML.

## SQL Server

SQL Server supports an extension to the ANSI standard allowing an additional `FROM` clause in `UPDATE` and `DELETE` statements, to limit modified rows by joining the target table to other tables. For `UPDATE`, you can set multiple columns simultaneously without repeating a sub-query. Warning: if a target row matches more than one joined row, an arbitrary (non-deterministic) value is chosen.

Syntax:

```sql
UPDATE <Table Name>
SET <Column Name> = <Expression> ,...
FROM <Table Source>
WHERE <Filter Predicate>;

DELETE FROM <Table Name>
FROM <Table Source>
WHERE <Filter Predicate>;
```

Example — delete customers with no orders:

```sql
DELETE FROM Customers
FROM Customers AS C
  LEFT OUTER JOIN Orders AS O ON O.Customer = C.Customer
WHERE O.OrderID IS NULL;
```

Example — update multiple columns from a join:

```sql
UPDATE O
SET Customer = OC.Customer, OrderDate = OC.OrderDate
FROM Orders AS O
  INNER JOIN OrderCorrections AS OC ON O.OrderID = OC.OrderID;
```

## PostgreSQL

Aurora PostgreSQL supports both joined forms, with different keywords: **`DELETE … USING from_list`** (the equivalent of SQL Server's second `FROM`) and **`UPDATE … FROM from_list`**. *(corrected: the original playbook said PostgreSQL has no joined `DELETE`.)* In both, the **target table is not repeated** in the `USING`/`FROM` list; join to it through the `WHERE` clause. Both support `RETURNING` (≈ `OUTPUT`).

Syntax:

```sql
[ WITH [ RECURSIVE ] with_query [, ...] ]
UPDATE [ ONLY ] table_name [ * ] [ [ AS ] alias ]
  SET { column_name = { expression | DEFAULT } |
    ( column_name [, ...] ) = ( { expression | DEFAULT } [, ...] ) |
    ( column_name [, ...] ) = ( sub-SELECT )
  } [, ...]
  [ FROM from_list ]
  [ WHERE condition | WHERE CURRENT OF cursor_name ]
  [ RETURNING * | output_expression [ [ AS ] output_name ] [, ...] ]
```

Joined `DELETE` (inner-join form) → `DELETE … USING`:

```sql
DELETE FROM customers c
USING blacklist b
WHERE c.customer = b.customer
RETURNING c.customer;
```

The playbook's "customers with no orders" example (a `LEFT JOIN … IS NULL` anti-join) is clearest as `NOT EXISTS`. Avoid `NOT IN (subquery)`, which returns no rows if the subquery yields any NULL:

```sql
DELETE FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer = c.customer);
```

`UPDATE … FROM`: name the target **once**, with an alias, and join through `WHERE` (verified on 18.6):

```sql
UPDATE orders o
SET customer = oc.customer, orderdate = oc.orderdate
FROM ordercorrections oc
WHERE o.orderid = oc.orderid
RETURNING o.*;
```

> **Do not** copy the SQL Server shape `UPDATE orders … FROM orders AS o JOIN …`. In PostgreSQL, a second `orders` in `FROM` is a separate table reference with no join condition to the target, so **every row of the target is updated** with values from an arbitrary matching row. The original playbook example had this bug.

## Summary

| Feature | SQL Server | Aurora PostgreSQL |
|---|---|---|
| Join as part of `DELETE` | `DELETE FROM t FROM t JOIN s …` | `DELETE FROM t USING s WHERE t.k = s.k` (or `NOT EXISTS` for anti-joins) |
| Join as part of `UPDATE` | `UPDATE alias SET … FROM t AS alias JOIN s …` | `UPDATE t alias SET … FROM s WHERE alias.k = s.k` (target not repeated) |
| `OUTPUT inserted.* / deleted.*` | Yes | `RETURNING *`; PG 18 also `RETURNING old.*, new.*` (verified) |
| `UPDATE TOP (n)` / `DELETE TOP (n)` | Yes | `WHERE ctid IN (SELECT ctid FROM t WHERE … LIMIT n)` (or the primary key) |

## Conversion notes
- `UPDATE ... FROM` is supported and largely compatible.
- `DELETE ... FROM <join>` → `DELETE … USING …` (inner joins) or `WHERE [NOT] EXISTS (…)` (anti/semi joins).
- `UPDATE … FROM` with several matching source rows: SQL Server picks an arbitrary one, and so does PostgreSQL. Either de-duplicate the source or use `MERGE`, which raises `MERGE command cannot affect row a second time` instead of guessing.
- `OUTPUT deleted.col, inserted.col` → PG 18 `RETURNING old.col, new.col` (verified on 18.6).
- Watch for non-deterministic results in SQL Server when joins produce multiple matches — re-validate logic after rewrite.
