# Views for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.views.html

**Conversion category:** Assisted (Four star feature compatibility)
**SCT automation:** N/A

**Key differences:** Minor syntax and handling differences. Indexes, triggers, and temporary views aren't supported.

## SQL Server

Views are stored virtual-table definitions (no data stored except indexed views). Used as abstraction layers and security filters. View definitions evaluated at creation and unaffected by later base-table changes; use `SCHEMABINDING` to prevent base object changes.

Updatable views require: single base table, directly referenced columns (no computed/aggregate/set-operator columns), and `CHECK OPTION` rows must remain in the view.

Special view types:
- **Indexed views** (materialized) — persisted in a unique clustered index, auto-updated.
- **Partitioned views** — `UNION ALL` of horizontally partitioned tables (DPV).
- **System views** — meta data, plus `INFORMATION_SCHEMA`.

### Syntax
```sql
CREATE [OR ALTER] VIEW [<Schema Name>.] <View Name> [(<Column Aliases> ])]
[WITH [ENCRYPTION][SCHEMABINDING][VIEW_METADATA]]
AS <SELECT Query>
[WITH CHECK OPTION][;]
```

### Examples

Standard view:
```sql
CREATE VIEW SalesView
AS
SELECT O.Customer,
    OI.Product,
    SUM(CAST(OI.Quantity AS BIGINT)) AS TotalItemsBought
FROM Orders AS O
    INNER JOIN
    OrderItems AS OI
        ON O.OrderID = OI.OrderID;
```

Indexed view:
```sql
CREATE VIEW SalesViewIndexed
AS
SELECT O.Customer, OI.Product, SUM_BIG(OI.Quantity) AS TotalItemsBought
FROM Orders AS O INNER JOIN OrderItems AS OI ON O.OrderID = OI.OrderID;

CREATE UNIQUE CLUSTERED INDEX IDX_SalesView
ON SalesViewIndexed (Customer, Product);
```

## MySQL

Aurora MySQL views are created with `CREATE VIEW`; the `SELECT` is evaluated at creation. Restrictions:
- No system/user-defined variables, no procedure/function parameters or local variables, no prepared statement parameters.
- All referenced objects must exist at creation.
- Cannot reference `TEMPORARY` tables; `TEMPORARY` views not supported.
- No triggers on views.
- Aliases limited to 64 characters.

Additional properties not in SQL Server:
- `ALGORITHM` clause — `MERGE` (merge into outer query) or `TEMPTABLE` (materialize).
- `DEFINER` and `SQL SECURITY` clauses for run-time permission context.

Supports updatable views and ANSI `CHECK OPTION` with `LOCAL`/`CASCADED` scope (default `CASCADED`). Non-updatable when view uses aggregates, `DISTINCT`, `GROUP BY`, `HAVING`, `UNION`/`UNION ALL`, subquery in select list, certain joins, `ALGORITHM = TEMPTABLE`, etc.

### Syntax
```sql
CREATE [OR REPLACE]
    [ALGORITHM = {UNDEFINED | MERGE | TEMPTABLE}]
    [DEFINER = { <User> | CURRENT_USER }]
    [SQL SECURITY { DEFINER | INVOKER }]
    VIEW <View Name> [(<Column List>)]
    AS <SELECT Statement>
    [WITH [CASCADED | LOCAL] CHECK OPTION];
```

### Examples
```sql
CREATE VIEW TotalSales
AS
SELECT Customer,
    SUM(TotalAmount) AS CustomerTotalAmount
GROUP BY Customer;
```

## Conversion notes

| Feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Indexed views | Supported | N/A | Use application-maintained tables. |
| Partitioned views | Supported | N/A | Can create, but no partition-elimination optimizations. |
| Updatable views | Supported | Supported | |
| Prevent schema conflicts | `SCHEMABINDING` | — | |
| Triggers on views | `INSTEAD OF` | N/A | |
| Temporary views | `CREATE VIEW #View…` | N/A | |
| Refresh view definition | `sp_refreshview` / `ALTER VIEW` | `ALTER VIEW` | |

- Basic syntax is ANSI compliant; migration is generally straightforward.
- `ORDER BY` allowed in Aurora MySQL view definition but ignored if outer SELECT has its own.
- Aurora MySQL has explicit security context (`DEFINER`/`SQL SECURITY`) to work around ownership-chain permissions.
- Unlike SQL Server, an Aurora MySQL view can invoke functions that change the database.
