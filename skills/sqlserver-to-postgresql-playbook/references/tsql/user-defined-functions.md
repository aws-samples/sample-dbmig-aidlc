# User-Defined Functions

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.udf.html

**Conversion category:** Assisted (three-star feature compatibility, three-star automation)
**SCT automation:** Three-star automation level; N/A action code

## SQL Server

UDFs accept input parameters and return a scalar value or a row set, implemented in T-SQL or CLR. Functions cannot modify data or database structure (only local scope objects). Functions are deterministic (same input → same result) or non-deterministic (e.g., current date/time). SQL Server has three T-SQL UDF types. SQL Server 2019 adds scalar UDF inlining for performance.

**Scalar UDF:**

```sql
CREATE FUNCTION <Function Name> ([{<Parameter Name> [AS] <Data Type> [= <Default Value>] [READONLY]} [,...n]])
RETURNS <Return Data Type>
[AS]
BEGIN
<Function Body Code>
RETURN <Scalar Expression>
END[;]
```
Example:

```sql
CREATE FUNCTION dbo.UpperCaseFirstChar (@String VARCHAR(20))
RETURNS VARCHAR(20)
AS
BEGIN
RETURN UPPER(LEFT(@String, 1)) + LOWER(SUBSTRING(@String, 2, 19))
END;

SELECT dbo.UpperCaseFirstChar ('mIxEdCasE'); -- Mixedcase
```

**Inline table-valued UDF** (view-like, parameterized; usable in FROM, with APPLY/OUTER APPLY):

```sql
CREATE FUNCTION <Function Name> ([params])
RETURNS TABLE
[AS]
RETURN (<SELECT Query>)[;]
```
Example:

```sql
CREATE FUNCTION dbo.EmployeeMonthlyOrders
(@EmployeeID INT)
RETURNS TABLE AS
RETURN
(
  SELECT EmployeeID, YEAR(OrderDate) AS OrderYear, MONTH(OrderDate) AS OrderMonth, COUNT(*) AS NumOrders
  FROM Orders AS O
  WHERE EmployeeID = @EmployeeID
  GROUP BY EmployeeID, YEAR(OrderDate), MONTH(OrderDate)
);
```

**Multi-statement table-valued UDF** (not limited to one SELECT; supports flow control; fewer optimizations, may be slower):

```sql
CREATE FUNCTION <Function Name> ([params])
RETURNS <@Return Variable> TABLE <Table Definition>
[AS]
BEGIN
<Function Body Code>
RETURN
END[;]
```

## PostgreSQL

PostgreSQL implements all functions via `CREATE FUNCTION` (see also the Stored Procedures reference). Syntax:

```sql
CREATE [ OR REPLACE ] FUNCTION
name ( [ [ argmode ] [ argname ] argtype [ { DEFAULT | = } default_expr ] [, ...]] )
[ RETURNS rettype
| RETURNS TABLE ( column_name column_type [, ...] ) ]
{ LANGUAGE lang_name
| TRANSFORM { FOR TYPE type_name } [, ... ]
| WINDOW
| IMMUTABLE | STABLE | VOLATILE | [ NOT ] LEAKPROOF
| CALLED ON NULL INPUT | RETURNS NULL ON NULL INPUT | STRICT
| [ EXTERNAL ] SECURITY INVOKER | [ EXTERNAL ] SECURITY DEFINER
| PARALLEL { UNSAFE | RESTRICTED | SAFE }
| COST execution_cost
| ROWS result_rows
| SET configuration_parameter { TO value | = value | FROM CURRENT }
| AS 'definition'
| AS 'obj_file', 'link_symbol'
} ...
[ WITH ( attribute [, ...] ) ]
```

## Conversion notes
- All three SQL Server UDF flavors map to PostgreSQL `CREATE FUNCTION`.
- Scalar UDF → `RETURNS <type>` with PL/pgSQL or SQL body.
- Inline table-valued UDF → `RETURNS TABLE(...)` or `RETURNS SETOF <type>` with a SQL `LANGUAGE sql` body for view-like optimization.
- Multi-statement table-valued UDF → `RETURNS TABLE(...)` with PL/pgSQL body.
- Mark functions `IMMUTABLE`/`STABLE`/`VOLATILE` to mirror determinism (helps the planner; `IMMUTABLE` ≈ deterministic).
- Remove `@` from parameter names; `APPLY`/`OUTER APPLY` → `LATERAL` joins (`CROSS JOIN LATERAL` / `LEFT JOIN LATERAL`).
- Use `SECURITY DEFINER`/`SECURITY INVOKER` for execution context.
