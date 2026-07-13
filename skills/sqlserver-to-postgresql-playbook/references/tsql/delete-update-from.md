# DELETE and UPDATE FROM

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.delete.html

**Conversion category:** Assisted (three-star feature compatibility, three-star automation)
**SCT automation:** Three-star automation level; N/A action code

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

Aurora PostgreSQL does **not** support `DELETE ... FROM from_list`, but it **does** support `UPDATE ... FROM`.

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

Rewrite `DELETE` with a subquery in the WHERE clause:

```sql
DELETE FROM Customers
WHERE Customer NOT IN (
  SELECT Customer FROM Orders
);
```

`UPDATE ... FROM` works directly:

```sql
UPDATE orders
SET Customer = OC.Customer, OrderDate = OC.OrderDate
FROM Orders AS O
  INNER JOIN OrderCorrections AS OC ON O.OrderID = OC.OrderID;
```

## Summary

| Feature | SQL Server | Aurora PostgreSQL |
|---|---|---|
| Join as part of `DELETE` | `DELETE FROM … FROM` | Not available. Rewrite with a WHERE-clause sub-query. |
| Join as part of `UPDATE` | `UPDATE … FROM` | `UPDATE … FROM` |

## Conversion notes
- `UPDATE ... FROM` is supported and largely compatible.
- `DELETE ... FROM <join>` must be rewritten as `DELETE ... WHERE <key> [NOT] IN (subquery)` or `WHERE EXISTS (...)`.
- Watch for non-deterministic results in SQL Server when joins produce multiple matches — re-validate logic after rewrite.
