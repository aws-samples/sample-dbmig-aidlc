# Tuning Run Plans

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tuning.plans.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): EXTENDED removed (verified); EXPLAIN ANALYZE TREE-only (verified); STATISTICS IO/TIME and Query Store replacements (Database Insights, digest tables).

Key differences: Syntax differences. Completely different optimizer with different operators and rules.

## SQL Server

Run plans provide detailed information about the data access and processing methods chosen by the SQL Server Query Optimizer, including estimated or actual costs of each operator and sub tree — critical data for troubleshooting query performance.

SQL Server returns run plans as plain text or XML. It produces a run plan when a query runs, but can also generate estimated plans without running the query. SQL Server Management Studio (SSMS) provides a graphical view of the underlying XML plan.

- Estimated run plan: `SET SHOWPLAN_XML`, `SHOWPLAN_ALL`, or `SHOWPLAN_TEXT`.
- Actual run plan (returns runtime statistics + warnings after execution): `SET STATISTICS XML` (returns XML document) or `STATISTICS PROFILE` (returns an additional result set with the plan).

SQL Server 2017+ introduces **automatic tuning**, which notifies users of potential performance issues (e.g., query run plan choice regressions) and can apply corrective actions automatically.

### Examples

Estimated run plan:

```sql
SET SHOWPLAN_XML ON;
SELECT *
FROM MyTable
WHERE SomeColumn = 3;
SET SHOWPLAN_XML OFF;
```

Actual run plan:

```sql
SET STATISTICS XML ON;
SELECT *
FROM MyTable
WHERE SomeColumn = 3;
SET STATISTICS XML OFF;
```

## MySQL

Amazon Aurora MySQL provides the `EXPLAIN`/`DESCRIBE` statement to display the run plan, usable with `SELECT`, `DELETE`, `INSERT`, `REPLACE`, and `UPDATE`.

- `EXPLAIN` returns the optimizer's run plan, including table joins and order.
- `EXPLAIN ... FOR CONNECTION <id>` returns the run plan for a statement running in a named connection.
- The `FORMAT` option selects either `TRADITIONAL` (tabular) or `JSON` output.
- Requires `SELECT` permission on all referenced tables/views; views require `SHOW VIEW`.
- MySQL Workbench provides a visual explain feature similar to SSMS graphical plans.
- `EXPLAIN ANALYZE` (MySQL 8.0.18+) provides expanded actual-vs-estimated cost information in `TREE` format (startup cost, total cost, rows returned, run loops). MySQL 8.0.21+ supports the `FORMAT=TREE` specifier (`TREE` is the only supported format).

### Syntax

```sql
{EXPLAIN | DESCRIBE | DESC} [FORMAT = TRADITIONAL | JSON | TREE]     -- EXTENDED was removed in 8.0 (verified)
EXPLAIN ANALYZE [FORMAT = TREE] <statement>
[SELECT statement | DELETE statement | INSERT statement | REPLACE statement | UPDATE
statement | FOR CONNECTION <connection id>]
```

### Examples

```sql
CREATE TABLE Employees
(
    EmployeeID INT NOT NULL PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    INDEX USING BTREE(Name)
);
```

```sql
EXPLAIN SELECT *
    FROM Employees
    WHERE Name = 'Jason';
```

```
id  select_type  table      partitions  type  possible_keys  key   key_len  ref    rows Extra
1   SIMPLE       Employees              ref   Name           Name  102      const  1
```

> To instruct the optimizer to use a join order matching the order tables are specified in a `SELECT`, use `SELECT STRAIGHT_JOIN`.

## Conversion notes

- Two-star feature compatibility; no SCT automation. The optimizers are completely different with different operators and rules, so plan analysis must be redone, not translated.
- SQL Server uses `SET SHOWPLAN_*` / `SET STATISTICS XML` / `STATISTICS PROFILE`; Aurora MySQL uses `EXPLAIN`/`DESCRIBE` (and `EXPLAIN ANALYZE` for actual costs in 8.0.18+).
- SQL Server returns XML/graphical plans (SSMS); MySQL returns tabular, JSON, or TREE format, with a visual explain in MySQL Workbench.
- SQL Server 2017+ automatic tuning (plan regression correction) has no direct Aurora MySQL equivalent.

Verified on Aurora MySQL 3.13 and 8.4.8:
- `EXPLAIN FORMAT=JSON` and `FORMAT=TREE` work; `EXPLAIN ANALYZE` works with `TREE` only (`FORMAT=JSON` → error 1235). Hash joins show as *Inner hash join*.
- `EXPLAIN ANALYZE` **executes** the statement (like `SET STATISTICS PROFILE ON`); run DML inside a transaction you roll back.
- 8.4 adds `explain_json_format_version` (1 by default; 2 = tree-shaped JSON); 3.x lacks it.
- `SET STATISTICS IO/TIME ON` → `EXPLAIN ANALYZE` timings, `SHOW SESSION STATUS LIKE 'Handler_read%'` before/after, or `performance_schema` statement events (enable `performance_schema`; off by default on Aurora, verified).
- Query Store → CloudWatch **Database Insights** (Performance Insights reached end of life on 2026-07-31) plus `performance_schema.events_statements_summary_by_digest` / `sys.statement_analysis`; MySQL keeps no plan history.
