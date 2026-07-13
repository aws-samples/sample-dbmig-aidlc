# User-defined functions for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.udf.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** Three star automation level

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

Aurora MySQL supports **scalar functions only** — no table-valued functions. Unlike SQL Server, routines **may read and write data** (`INSERT`/`UPDATE`/`DELETE`) and run DDL (`CREATE`/`DROP`), but **cannot** contain explicit transaction statements (`COMMIT`/`ROLLBACK`).

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
- Aurora MySQL function rules are more lenient (can modify data/schema) — guard against unexpected side effects.
- Inline TVF → use **views**, replacing parameters with `WHERE` filter predicates in the calling code.
- Multi-statement TVF → rewrite as a **stored procedure** that populates a temp/standard table; read from the table directly.

| SQL Server UDF feature | Migrate to Aurora MySQL | Comment |
|---|---|---|
| Scalar UDF | Scalar UDF | `CREATE FUNCTION`, remove `AS` |
| Inline table-valued UDF | N/A | Use views + `WHERE` predicates |
| Multi-statement table-valued UDF | N/A | Use stored procedures populating tables |
| Determinism implicit | Explicit declaration | Use `DETERMINISTIC` |
| Boundaries local only | Can change data and schema | More lenient — avoid unexpected changes |
