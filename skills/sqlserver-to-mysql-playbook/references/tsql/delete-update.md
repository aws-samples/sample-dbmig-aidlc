# DELETE and UPDATE FROM for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.deleteupdate.html

**Conversion category:** Automatic (Four star feature compatibility — but requires rewrite to subqueries)
**SCT automation:** Four star automation level

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

Aurora MySQL does **not** support `DELETE … FROM … FROM` or `UPDATE … FROM` syntax. Rewrite as subqueries.

- `DELETE`: put the subquery in the `WHERE` clause.
- `UPDATE`: put correlated subqueries in the `SET` clause (one per column), and add a `WHERE` clause to limit rows.

### Examples

```sql
-- Delete customers with no orders
DELETE FROM Customers
WHERE Customer NOT IN (
    SELECT Customer
    FROM Orders
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
- Aurora MySQL `UPDATE` differs: can update multiple tables in one statement; expressions evaluated left-to-right (not all-at-once). E.g. `UPDATE Table SET Col1 = Col1 + 1, Col2 = Col1` → `Col2` gets the *new* `Col1`.

| Feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Join as part of `DELETE` | `DELETE FROM … FROM` | N/A | Rewrite using `WHERE` with subquery |
| Join as part of `UPDATE` | `UPDATE … FROM` | N/A | Rewrite using correlated subquery in `SET`, add `WHERE` |
