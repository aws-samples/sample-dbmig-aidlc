# DELETE and UPDATE FROM for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.deleteupdate.html

**Conversion category:** Automatic (Four star feature compatibility — but requires rewrite to subqueries)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): *(corrected)* MySQL supports multi-table UPDATE … JOIN and DELETE t FROM … JOIN (verified) — preferred over correlated subqueries; fixed the NOT IN null trap; left-to-right SET evaluation (verified 2,2); LIMIT on multi-table DML rejected (1221, verified); OUTPUT has no equivalent.

## SQL Server

SQL Server extends ANSI with an additional `FROM` clause in `UPDATE`/`DELETE`, allowing joins to other tables to limit affected rows (similar to a `WHERE` with a derived subquery). For `UPDATE`, multiple columns can be set without repeating the subquery. Risk: if a row matches more than one joined row, an arbitrary value is chosen (non-deterministic).

### Syntax

```sql
UPDATE <Table Name>
SET <Column Name> = <Expression> ,...
FROM <Table Source>
WHERE <Filter Predicate>;

DELETE FROM <Table Name>
FROM <Table Source>
WHERE <Filter Predicate>;
```

### Examples

```sql
-- Delete customers with no orders
DELETE FROM Customers
FROM Customers AS C
    LEFT OUTER JOIN
    Orders AS O
    ON O.Customer = C.Customer
WHERE O.OrderID IS NULL;

-- Update multiple columns from another table
UPDATE O
SET Customer = OC.Customer,
    OrderDate = OC.OrderDate
FROM Orders AS O
    INNER JOIN
    OrderCorrections AS OC
    ON O.OrderID = OC.OrderID;
```

## MySQL

Aurora MySQL does **not** support the T-SQL `DELETE … FROM … FROM` or `UPDATE … SET … FROM` syntax, but it **does** support **multi-table `UPDATE` and `DELETE` with joins**, which is the closest and usually fastest conversion (verified on 3.13 and 8.4.8):

```sql
-- SQL Server: UPDATE o SET o.Customer = oc.Customer, o.OrderDate = oc.OrderDate
--             FROM Orders o JOIN OrderCorrections oc ON o.OrderID = oc.OrderID
UPDATE Orders o
JOIN OrderCorrections oc ON o.OrderID = oc.OrderID
SET o.Customer = oc.Customer, o.OrderDate = oc.OrderDate;

-- SQL Server: DELETE c FROM Customers c LEFT JOIN Orders o ON o.Customer = c.Customer WHERE o.OrderID IS NULL
DELETE c FROM Customers c
LEFT JOIN Orders o ON o.Customer = c.Customer
WHERE o.OrderID IS NULL;
```

The subquery forms below (from the original playbook) also work:

- `DELETE`: put the subquery in the `WHERE` clause.
- `UPDATE`: put correlated subqueries in the `SET` clause (one per column), and add a `WHERE` clause to limit rows.

### Examples

```sql
-- Delete customers with no orders
DELETE FROM Customers
WHERE NOT EXISTS (                  -- the original used NOT IN, which deletes nothing if Orders.Customer contains a NULL
    SELECT 1
    FROM Orders
    WHERE Orders.Customer = Customers.Customer
);

-- Update multiple columns via correlated subqueries
UPDATE Orders
SET Customer = (
    SELECT Customer
    FROM OrderCorrections AS OC
    WHERE Orders.OrderID = OC.OrderID
),
OrderDate = (
    SELECT OrderDate
    FROM OrderCorrections AS OC
    WHERE Orders.OrderID = OC.OrderID
)
WHERE OrderID IN (
    SELECT OrderID
    FROM OrderCorrections
);
```

## Conversion notes

- Rewrite `DELETE FROM…FROM` → `WHERE` clause with subquery (usually simpler/clearer).
- Rewrite `UPDATE…FROM` → correlated subquery per column in `SET`, plus a limiting `WHERE`.
- Always add a `WHERE` clause to `UPDATE` rewrites even if the SQL Server original limited rows only by the join.
- If a correlated subquery returns more than one row, Aurora MySQL raises `SQL Error [1242] [21000]: Subquery returns more than 1 row` (SQL Server silently picked an arbitrary value).
- Aurora MySQL `UPDATE` differs: can update multiple tables in one statement; single-table assignments are evaluated **left-to-right** (not all-at-once). `UPDATE t SET c1 = c1 + 1, c2 = c1` → `c2` gets the *new* `c1` (verified: 2, 2; SQL Server gives 2, 1). Reorder assignments or use the old value explicitly.
- Prefer the multi-table `UPDATE … JOIN` / `DELETE t FROM … JOIN` forms over correlated subqueries: one pass, no error 1242, and the same semantics as T-SQL joins (an arbitrary row wins if the join matches several source rows, as in SQL Server).
- A table cannot be updated and read in a subquery of the same statement (error 1093); wrap the subquery in a derived table or use the join form.

| Feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Join as part of `DELETE` | `DELETE FROM … FROM` | `DELETE t FROM t JOIN …` | multi-table delete (verified) |
| Join as part of `UPDATE` | `UPDATE … FROM` | `UPDATE t JOIN … SET …` | multi-table update; can update several tables at once (verified) |
| `UPDATE TOP (n)` / `DELETE TOP (n)` | `TOP (n)` | `ORDER BY … LIMIT n` (single-table only) | multi-table forms reject `LIMIT` (error 1221, verified) |
| `OUTPUT inserted.* / deleted.*` | `OUTPUT` | none | read rows before/after in the same transaction, or use triggers |
