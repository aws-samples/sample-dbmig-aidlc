# Temporal Tables (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.temporaltables.html

**Conversion category:** Manual (Two-star compatibility, no automation)
**SCT automation:** N/A — no automated conversion.

## SQL Server

System-versioned temporal tables (ANSI SQL 2011; T-SQL since SQL Server 2016). Each table has two `DATETIME2` period columns and an associated history table that retains prior row versions.

Query history with `FOR SYSTEM_TIME` plus: `ALL`, `CONTAINED IN`, `AS OF`, `BETWEEN`.

Anomaly detection example:
```sql
CREATE TABLE Products_returned
(
  ProductID int NOT NULL PRIMARY KEY CLUSTERED,
  ProductName varchar(60) NOT NULL,
  return_count INT NOT NULL,
  ValidFrom datetime2(7) GENERATED ALWAYS AS ROW START NOT NULL,
  ValidTo datetime2(7) GENERATED ALWAYS AS ROW END NOT NULL,
  PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
)
WITH( SYSTEM_VERSIONING = ON (HISTORY_TABLE = dbo.ProductHistory,
  DATA_CONSISTENCY_CHECK = ON ))
```

Audit example:
```sql
CREATE TABLE Employee
(
  EmployeeID int NOT NULL PRIMARY KEY CLUSTERED,
  Name nvarchar(60) NOT NULL,
  Salary decimal (6,2) NOT NULL,
  ValidFrom datetime2 (2) GENERATED ALWAYS AS ROW START,
  ValidTo datetime2 (2) GENERATED ALWAYS AS ROW END,
  PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
)
WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = dbo.EmployeeTrackHistory));

SELECT * FROM Employee
  FOR SYSTEM_TIME ALL WHERE
    EmployeeID = 1000 ORDER BY ValidFrom;
```

Other scenarios: fixing row-level corruption, slowly changing dimensions, over-time change analysis.

## PostgreSQL

PostgreSQL has a temporal-tables extension, but it is **not supported by Amazon Aurora**. Workaround: create table triggers that update a custom history table to track data changes. See Triggers.

## Conversion notes
- No native temporal-table support in Aurora PostgreSQL and no SCT automation.
- Manually implement system versioning with a custom history table plus `AFTER INSERT/UPDATE/DELETE` triggers maintaining `ValidFrom`/`ValidTo` period columns.
- `FOR SYSTEM_TIME` query clauses must be rewritten as explicit queries against the custom history table.
