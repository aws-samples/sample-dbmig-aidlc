# Views (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.views.html

**Conversion category:** Assisted (Four-star compatibility, four-star automation)
**SCT automation:** N/A. Key difference: PostgreSQL doesn't support indexed or partitioned views.

## SQL Server

Views are stored query definitions (virtual tables). Except for indexed views, they store no data and are re-evaluated each invocation. Used as abstraction layers and security filters.

Updatable views require: DML targets one base table; modified columns reference base-table columns directly (no computed/aggregate/expression columns); `CHECK OPTION` prevents updates that filter rows out of the view.

Three specialized types:
- **Indexed views** (materialized/persisted via unique clustered index, auto-maintained).
- **Partitioned views** (`UNION ALL` over horizontally partitioned tables; Distributed Partitioned Views).
- **System views** (`INFORMATION_SCHEMA`, metadata).

Syntax:
```sql
CREATE [OR ALTER] VIEW [<Schema Name>.] <View Name> [(<Column Aliases> ])]
[WITH [ENCRYPTION][SCHEMABINDING][VIEW_METADATA]]
AS <SELECT Query>
[WITH CHECK OPTION][;]
```

Examples:
```sql
-- Standard view
CREATE VIEW SalesView
AS
SELECT O.Customer,
  OI.Product,
  SUM(CAST(OI.Quantity AS BIGINT)) AS TotalItemsBought
FROM Orders AS O
  INNER JOIN OrderItems AS OI
  ON O.OrderID = OI.OrderID;

-- Indexed view
CREATE VIEW SalesViewIndexed
AS
SELECT O.Customer, OI.Product,
  SUM_BIG(OI.Quantity) AS TotalItemsBought
FROM Orders AS O
  INNER JOIN OrderItems AS OI ON O.OrderID = OI.OrderID;
CREATE UNIQUE CLUSTERED INDEX IDX_SalesView
ON SalesViewIndexed (Customer, Product);

-- Partitioned view
CREATE VIEW dbo.PartitioneView
WITH SCHEMABINDING
AS
SELECT * FROM Table1
UNION ALL SELECT * FROM Table2
UNION ALL SELECT * FROM Table3
```

## PostgreSQL

Basic views are similar. Indexed and partitioned views are not supported (may require redesign/rewrite). Simple views are automatically updatable; no DML restrictions on updatable columns (read-only columns raise an error on INSERT/UPDATE).

Note: For RDS PostgreSQL 13+, rename a view column with `ALTER VIEW ... RENAME COLUMN`; for older versions use `ALTER TABLE`.

Privileges: grant `SELECT` and DML on base tables/views to the role.

Syntax:
```sql
CREATE [ OR REPLACE ] [ TEMP | TEMPORARY ] [ RECURSIVE ] VIEW name [ ( column_name [,...] ) ]
[ WITH ( view_option_name [= view_option_value] [, ... ] ) ]
AS query
[ WITH [ CASCADED | LOCAL ] CHECK OPTION ]
```

`CHECK OPTION`: `LOCAL` verifies without hierarchical check; `CASCADED` verifies all underlying base views hierarchically.

Examples:
```sql
-- View without CHECK OPTION (update succeeds)
CREATE OR REPLACE VIEW VW_DEP AS
  SELECT DEPARTMENT_ID, DEPARTMENT_NAME, MANAGER_ID, LOCATION_ID
  FROM DEPARTMENTS
  WHERE LOCATION_ID=1700;
UPDATE VW_DEP SET LOCATION_ID=1600;  -- 21 rows updated

-- View with LOCAL CHECK OPTION (update violating predicate fails)
CREATE OR REPLACE VIEW VW_DEP AS
  SELECT DEPARTMENT_ID, DEPARTMENT_NAME, MANAGER_ID, LOCATION_ID
  FROM DEPARTMENTS
  WHERE LOCATION_ID=1700
  WITH LOCAL CHECK OPTION;
UPDATE VW_DEP SET LOCATION_ID=1600;  -- ERROR: new row violates check option
```

## Conversion notes

| Feature | SQL Server | Aurora PostgreSQL |
|---|---|---|
| Indexed views | Supported | N/A |
| Partitioned views | Supported | N/A |
| Updateable views | Supported | Supported |
| Prevent schema conflicts | `SCHEMABINDING` | N/A |
| Triggers on views | `INSTEAD OF` | `INSTEAD OF` |
| Temporary views | `CREATE VIEW #View…` | `CREATE [OR REPLACE] [TEMP] [TEMPORARY] VIEW` |
| Refresh view definition | `sp_refreshview` / `ALTER VIEW` | `ALTER VIEW` |

- Indexed views: redesign (e.g., use materialized views with manual refresh, or summary tables).
- Partitioned views: redesign using native partitioning or `UNION ALL` views without index optimization.
- No `SCHEMABINDING` equivalent.
- Simple PostgreSQL views are automatically updatable; `INSTEAD OF` triggers available for complex cases.
