# Temporal Tables (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.temporaltables.html

**Conversion category:** Manual (Two-star compatibility, no automation)
**SCT automation:** N/A — no automated conversion.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): `temporal_tables` extension unavailable (verified), history-table trigger template and `AS OF` rewrite, PG 18 `WITHOUT OVERLAPS` temporal keys (verified).

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

PostgreSQL has no system-versioned tables, and the community `temporal_tables` extension is **not available on Aurora PostgreSQL 18** (checked against `pg_available_extensions` on 18.6). Implement system versioning with a history table and a trigger:

```sql
CREATE TABLE employee (
  employee_id int PRIMARY KEY, name varchar(60) NOT NULL, salary numeric(6,2) NOT NULL,
  valid_from timestamptz NOT NULL DEFAULT clock_timestamp(),
  valid_to   timestamptz NOT NULL DEFAULT 'infinity');
CREATE TABLE employee_history (LIKE employee);

CREATE FUNCTION employee_versioning() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  -- close the old version and archive it
  INSERT INTO employee_history (employee_id, name, salary, valid_from, valid_to)
  VALUES (OLD.employee_id, OLD.name, OLD.salary, OLD.valid_from, clock_timestamp());
  IF TG_OP = 'UPDATE' THEN NEW.valid_from := clock_timestamp(); RETURN NEW; END IF;
  RETURN COALESCE(NEW, OLD);
END $$;
CREATE TRIGGER employee_versioning BEFORE UPDATE OR DELETE ON employee
  FOR EACH ROW EXECUTE FUNCTION employee_versioning();

-- FOR SYSTEM_TIME AS OF t  →
SELECT * FROM employee WHERE valid_from <= :t AND valid_to > :t
UNION ALL
SELECT * FROM employee_history WHERE valid_from <= :t AND valid_to > :t;
```

**PostgreSQL 18 temporal constraints** cover the *application-time* side of ANSI SQL:2011, which SQL Server lacks: `PRIMARY KEY (id, valid_period WITHOUT OVERLAPS)` and `FOREIGN KEY (…, PERIOD valid_period) REFERENCES …` on `daterange`/`tstzrange` columns (needs `btree_gist`, verified on 18.6). They prevent overlapping validity periods in the history table, for example:
```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE TABLE employee_history2 (employee_id int, valid tstzrange, salary numeric,
  PRIMARY KEY (employee_id, valid WITHOUT OVERLAPS));
```

## Conversion notes
- No native system-versioned tables in Aurora PostgreSQL 18 and no SCT automation.
- Manually implement system versioning with a custom history table plus a trigger maintaining the period columns (template above). Use `clock_timestamp()`, not `now()`, if several versions can be written in one transaction. Note that `now()` matches SQL Server's transaction-start period semantics more closely; choose deliberately.
- Load existing SQL Server history rows into the history table during migration (DMS can copy the `…History` table as an ordinary table).
- `FOR SYSTEM_TIME` query clauses must be rewritten as explicit queries against the custom history table.
