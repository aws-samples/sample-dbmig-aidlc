# Dynamic SQL

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.dynamicsql.html

**Conversion category:** Manual (two-star feature compatibility — different paradigm requires rewriting; five-star SCT automation)
**SCT automation:** Five-star automation level; N/A action code

## SQL Server

Dynamic SQL minimizes hard-coded SQL and lets developers construct/run queries at run time as strings. Two options: `EXECUTE` command or `sp_executesql`.

**EXECUTE command** — runs a command string within a T-SQL block/procedure/function, can use linked servers, and define result-set metadata via `WITH RESULT SETS`. Validate the string before running.

```sql
-- run a character string:
{ EXEC | EXECUTE }
  ( { @string_variable | [ N ]'tsql_string' } [ + ...n ] )
  [ AS { LOGIN | USER } = ' name ' ]
[;]
```

Examples:

> ⚠️ **INSECURE EXAMPLE — DO NOT USE IN PRODUCTION.** The `EXECUTE('...' + @var + '...')` form below
> concatenates variables directly into the command string. If any variable is derived from user
> input, this is a **SQL injection** vulnerability. It is shown only to illustrate the legacy
> `EXECUTE` string form; **use the parameterized `sp_executesql` pattern (below) instead**, and for
> dynamic *identifiers* (schema/table/column names, which cannot be parameters) validate against an
> allowlist and wrap them with `QUOTENAME()`.

```sql
-- ANTI-PATTERN (unsafe): raw string concatenation of identifiers into dynamic SQL.
DECLARE @scm_name sysname;
DECLARE @tbl_name sysname;
EXECUTE ('DROP TABLE ' + @scm_name + '.' + @tbl_name + ';');            -- ❌ injectable

-- switch context:
EXECUTE ('DROP TABLE ' + @scm_name + '.' + @tbl_name + ';') AS USER = 'SchemasAdmin';  -- ❌ injectable

-- with result set:
EXEC GetMaxSalByDeptID 23
WITH RESULT SETS ( ([Salary] int NOT NULL) );
```

> **Safe form of the above:** quote the identifiers with `QUOTENAME()` (which also validates them):
> `SET @sql = N'DROP TABLE ' + QUOTENAME(@scm_name) + N'.' + QUOTENAME(@tbl_name) + N';'; EXEC sp_executesql @sql;`
> — never concatenate a raw identifier, and pass all *values* as `sp_executesql` parameters.

**sp_executesql** — runs a parameterized T-SQL command/block repeatedly with embedded parameters.

```sql
sp_executesql [ @stmt = ] statement
[ { , [ @params = ] N'@parameter_name data_type [ OUT | OUTPUT ][ ,...n ]' }
    { , [ @param1 = ] 'value1' [ ,...n ] } ]
```

```sql
EXECUTE sp_executesql
  N'SELECT * FROM HR.Employees WHERE DeptID = @DID',
  N'@DID int',
  @DID = 23;
```

## PostgreSQL

PostgreSQL `EXECUTE` prepares and runs commands dynamically (SELECT, DML, DDL), and supports bind variables. Converting SQL Server dynamic SQL requires significant effort.

SELECT with dynamic table name + bind variable:

```sql
DO $$DECLARE
Tabname varchar(30) := 'employees';
num integer := 1;
cnt integer;
BEGIN
EXECUTE format('SELECT count(*) FROM %I WHERE manager = $1', tabname)
INTO cnt USING num;
RAISE NOTICE 'Count is % int table %', cnt, tabname;
END$$;
```

DML, without and with variables:

```sql
DO $$DECLARE
BEGIN
EXECUTE 'INSERT INTO numbers (a) VALUES (1)';
EXECUTE format('INSERT INTO numbers (a) VALUES (%s)', 42);
END$$;
```

> `%s` formats as a simple string (null → empty string). `%I` treats the value as an SQL identifier, double-quoting if needed (null is an error).

DDL:

```sql
DO $$DECLARE
BEGIN
EXECUTE 'CREATE TABLE numbers (num integer)';
END$$;
```

**PREPARE** — improves performance of reusable statements (SELECT/INSERT/UPDATE/DELETE/VALUES). Scope is the current session; a DDL change on a referenced object forces a hard parse on the next EXECUTE.

```sql
PREPARE numplan (int, text, bool) AS
INSERT INTO numbers VALUES($1, $2, $3);
EXECUTE numplan(100, 'New number 100', 't');
EXECUTE numplan(101, 'New number 101', 't');
EXECUTE numplan(102, 'New number 102', 'f');
```

## Summary

| Functionality | SQL Server dynamic SQL | PostgreSQL EXECUTE/PREPARE |
|---|---|---|
| Run SQL with results + bind variables | `DECLARE @sal int; EXECUTE getSalary @sal OUTPUT;` | `EXECUTE format('select salary from employees WHERE %I = $1', col_name) INTO amount USING col_val;` |
| Run DML with variables + bind variables | build string `SET @sqlCommand = 'UPDATE employees SET salary=salary' + @amount ...; EXECUTE (@sqlCommand)` | `EXECUTE format('UPDATE employees SET salary = salary + $1 WHERE %I = $2', col_name) USING amount, col_val;` |
| Run DDL | `EXECUTE ('CREATE TABLE link_emp (...);');` | `EXECUTE 'CREATE TABLE link_emp (...)';` |
| Run anonymous block | `BEGIN ... END;` | `DO $$DECLARE BEGIN ... END$$;` |

## Conversion notes
- No `sp_executesql` — use `EXECUTE ... USING` with `format()` for parameterized dynamic SQL.
- Use `format()` with `%I` (identifiers) and `%s`/`%L` (values/literals) instead of string concatenation — safer against SQL injection and handles quoting.
- Bind values with `USING`; capture results with `INTO`.
- Dynamic SQL must live inside a PL/pgSQL block (`DO $$ ... $$` or function), not standalone.
- `EXECUTE AS USER` context switching has no direct equivalent — handle via roles/`SET ROLE`.
- Use `PREPARE`/`EXECUTE` for repeated statements to gain performance.
