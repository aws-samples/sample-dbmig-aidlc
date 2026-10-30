# User-defined functions for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.udf.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** Three star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected 'functions can run DDL' (error 1422 — verified); self-table DML (1442), no UDFs in generated columns/functional indexes (verified), no defaults/overloading, binlog creation rule, LATERAL and JSON_TABLE for TVF patterns.

## SQL Server

UDFs accept input parameters and return a scalar value or a row set. Implemented in T-SQL or CLR (CLR not covered). Functions can't have lasting database impact — can't modify data or schema, only local objects. May be deterministic or non-deterministic. Three T-SQL UDF types: scalar, inline table-valued, multi-statement table-valued. SQL Server 2019 adds scalar UDF inlining for performance.

### Scalar UDF

```sql
CREATE FUNCTION <Function Name> ([{<Parameter Name> [AS] <Data Type> [= <Default Value>] [READONLY]} [,...n]])
RETURNS <Return Data Type>
[AS]
BEGIN
<Function Body Code>
RETURN <Scalar Expression>
END[;]

CREATE FUNCTION dbo.UpperCaseFirstChar (@String VARCHAR(20))
RETURNS VARCHAR(20)
AS
BEGIN
RETURN UPPER(LEFT(@String, 1)) + LOWER(SUBSTRING(@String, 2, 19))
END;
```

### Inline table-valued UDF

Like a parameterized view/CTE; usable in `FROM` and with `APPLY`/`OUTER APPLY`.

```sql
CREATE FUNCTION <Function Name> ([params])
RETURNS TABLE
[AS]
RETURN (<SELECT Query>)[;]

CREATE FUNCTION dbo.EmployeeMonthlyOrders (@EmployeeID INT)
RETURNS TABLE AS
RETURN
(
SELECT EmployeeID, YEAR(OrderDate) AS OrderYear, MONTH(OrderDate) AS OrderMonth, COUNT(*) AS NumOrders
FROM Orders AS O
WHERE EmployeeID = @EmployeeID
GROUP BY EmployeeID, YEAR(OrderDate), MONTH(OrderDate)
);
```

### Multi-statement table-valued UDF

Like inline TVF but allows multiple statements (flow control, complex processing); fewer optimizations, potentially slower.

```sql
CREATE FUNCTION <Function Name> ([params])
RETURNS <@Return Variable> TABLE <Table Definition>
[AS]
BEGIN
<Function Body Code>
RETURN
END[;]
```

## MySQL

Aurora MySQL supports **scalar functions only** — no table-valued functions. Unlike SQL Server, functions **may write data** (`INSERT`/`UPDATE`/`DELETE`, verified), but *(corrected)* they **cannot run DDL or `COMMIT`/`ROLLBACK`** (error 1422 for `CREATE TABLE` in a function, verified on 3.13 and 8.4.8) and cannot use dynamic SQL (error 1336).

Characteristics (saved with the definition, viewable via `SHOW CREATE FUNCTION`):
- `DETERMINISTIC` must be stated explicitly (engine assumes non-deterministic otherwise; validity not checked — wrong declaration causes unexpected results).
- `CONTAINS SQL` / `NO SQL` / `READS SQL DATA` / `MODIFIES SQL DATA` — advisory only (not enforced).

### Syntax

```sql
CREATE FUNCTION <Function Name> ([<Function Parameter>[,...]])
RETURNS <Returned Data Type> [characteristic ...]
<Function Code Body>

-- characteristic:
-- COMMENT '<Comment>' | LANGUAGE SQL | [NOT] DETERMINISTIC
-- | { CONTAINS SQL | NO SQL | READS SQL DATA | MODIFIES SQL DATA }
-- | SQL SECURITY { DEFINER | INVOKER }
```

### Example

```sql
CREATE FUNCTION UpperCaseFirstChar (String VARCHAR(20))
RETURNS VARCHAR(20)
BEGIN
RETURN CONCAT(UPPER(LEFT(String, 1)) , LOWER(SUBSTRING(String, 2, 19)));
END

SELECT UpperCaseFirstChar ('mIxEdCasE');  -- Mixedcase
```

## Conversion notes

- Scalar UDFs migrate easily: similar syntax, but **remove the `AS` keyword** (invalid in Aurora MySQL) and drop `@` from parameter names.
- Function determinism is implicit in SQL Server but must be **explicitly** declared `DETERMINISTIC` in Aurora MySQL (enables optimizations).
- Aurora MySQL function rules are more lenient for data (DML allowed) but not for schema (DDL rejected) — guard against unexpected side effects. A function that modifies a table cannot be called from a statement that uses the same table (error 1442, verified).
- User functions cannot be used in generated columns or functional indexes (errors 3763/3758, verified) — SQL Server persisted computed columns that call a UDF need a trigger-maintained column instead.
- No parameter defaults, no overloading (error 1304), names ≤ 64 characters; parameters lose the `@` prefix. Declare `tinyint`/`smallint` parameters as `INT` when callers pass integer literals.
- `WITH SCHEMABINDING` / `RETURNS NULL ON NULL INPUT` have no equivalents.
- With binary logging on, creating a function that is not `DETERMINISTIC`/`NO SQL`/`READS SQL DATA` needs `log_bin_trust_function_creators` = 1 (0 by default, verified).
- Inline TVFs used with `CROSS APPLY` → a view or derived table joined with `JOIN LATERAL` (MySQL 8.0.14+); TVFs that return parsed rows from a string → `JSON_TABLE` (see `string-functions.md`).
- Inline TVF → use **views**, replacing parameters with `WHERE` filter predicates in the calling code.
- Multi-statement TVF → rewrite as a **stored procedure** that populates a temp/standard table; read from the table directly.

| SQL Server UDF feature | Migrate to Aurora MySQL | Comment |
|---|---|---|
| Scalar UDF | Scalar UDF | `CREATE FUNCTION`, remove `AS` |
| Inline table-valued UDF | N/A | Use views + `WHERE` predicates |
| Multi-statement table-valued UDF | N/A | Use stored procedures populating tables |
| Determinism implicit | Explicit declaration | Use `DETERMINISTIC` |
| Boundaries local only | Can change data (not schema) | DML allowed, DDL/COMMIT rejected (verified) |
