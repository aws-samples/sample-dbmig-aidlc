# User-Defined Functions

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.udf.html

**Conversion category:** Assisted (three-star feature compatibility, three-star automation)
**SCT automation:** Three-star automation level; N/A action code

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Added verified patterns: SQL-standard RETURN/BEGIN ATOMIC bodies (PG 14), inlined LANGUAGE sql table functions (EXPLAIN-checked) vs materialized PL/pgSQL multi-statement TVFs, APPLY→LATERAL, volatility, STRICT, parameter-type and SCHEMABINDING mappings.

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

## PostgreSQL 18 patterns (verified on Aurora PostgreSQL 18.6)

```sql
-- Scalar UDF → SQL-standard body (PG 14): parsed at CREATE time, dependencies tracked,
-- and inlined into the calling query by the planner (like SQL Server 2019 scalar UDF inlining)
CREATE OR REPLACE FUNCTION uppercasefirstchar(p_string varchar)
RETURNS varchar LANGUAGE sql IMMUTABLE PARALLEL SAFE
RETURN upper(left(p_string, 1)) || lower(substring(p_string FROM 2 FOR 19));

-- Inline TVF → LANGUAGE sql RETURNS TABLE, STABLE: inlined like a view
-- (verified: EXPLAIN shows a scan of the base table, no Function Scan)
CREATE OR REPLACE FUNCTION employee_monthly_orders(p_employeeid int)
RETURNS TABLE (employeeid int, orderyear int, ordermonth int, numorders bigint)
LANGUAGE sql STABLE
BEGIN ATOMIC
  SELECT o.employeeid, extract(year FROM o.orderdate)::int, extract(month FROM o.orderdate)::int, count(*)
  FROM orders o WHERE o.employeeid = p_employeeid
  GROUP BY 1, 2, 3;
END;

-- Multi-statement TVF → PL/pgSQL RETURNS TABLE with RETURN QUERY / RETURN NEXT
-- (always a Function Scan: the result is materialized, the planner estimates ROWS 1000)
CREATE OR REPLACE FUNCTION mstvf(p int) RETURNS TABLE (id int, v text)
LANGUAGE plpgsql STABLE AS $$
BEGIN
  RETURN QUERY SELECT g, 'x' FROM generate_series(1, p) g;
  id := 99; v := 'extra'; RETURN NEXT;
END $$;
```

- `CROSS APPLY dbo.f(t.col)` → `CROSS JOIN LATERAL f(t.col)`; `OUTER APPLY` → `LEFT JOIN LATERAL f(t.col) ON true`.
- Inlining of a SQL table function needs: `LANGUAGE sql`, a single `SELECT`, `STABLE` or `IMMUTABLE`, not `SECURITY DEFINER`, not `STRICT`, and no `SET` clause. A `RETURNS TABLE` column named like a table column is ambiguous inside PL/pgSQL; qualify columns with a table alias (as above) or set `#variable_conflict use_column`.
- Volatility: SQL Server deterministic → `IMMUTABLE` only if the body reads no tables and no session settings; functions that read tables → `STABLE`; `GETDATE()`/`NEWID()`/`RAND()` inside → `VOLATILE`. Mislabeling as `IMMUTABLE` gives stale results in indexes and cached plans.
- SQL Server returns NULL from a scalar UDF only when the body does; add `STRICT` (`RETURNS NULL ON NULL INPUT`) only when that matches the source logic, because `STRICT` also blocks inlining.
- Parameter types: declare `tinyint`/`smallint` parameters as `integer` (see `engines/sqlserver-to-postgresql/checks/non-portable-constructs.md` §16); PostgreSQL resolves overloaded functions by type and does not narrow `integer` arguments.
- Callers using `dbo.f(…)`: the schema prefix becomes the target schema the toolkit mapped `dbo` to; unqualified calls depend on `search_path`.
- `WITH SCHEMABINDING` → a `BEGIN ATOMIC`/`RETURN` SQL body gives the same protection: dropping a referenced table is blocked by the dependency.
- `WITH RETURNS NULL ON NULL INPUT` (SQL Server 2014+) → `STRICT`. `WITH INLINE = ON/OFF` has no equivalent; inlining is decided by the planner.

## Conversion notes
- All three SQL Server UDF flavors map to PostgreSQL `CREATE FUNCTION`.
- Scalar UDF → `RETURNS <type>` with PL/pgSQL or SQL body.
- Inline table-valued UDF → `RETURNS TABLE(...)` or `RETURNS SETOF <type>` with a SQL `LANGUAGE sql` body for view-like optimization.
- Multi-statement table-valued UDF → `RETURNS TABLE(...)` with PL/pgSQL body.
- Mark functions `IMMUTABLE`/`STABLE`/`VOLATILE` to mirror determinism (helps the planner; `IMMUTABLE` ≈ deterministic).
- Remove `@` from parameter names; `APPLY`/`OUTER APPLY` → `LATERAL` joins (`CROSS JOIN LATERAL` / `LEFT JOIN LATERAL`).
- Use `SECURITY DEFINER`/`SECURITY INVOKER` for execution context.
