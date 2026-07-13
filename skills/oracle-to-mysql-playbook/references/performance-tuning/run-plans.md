# Oracle and MySQL Run Plans

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tuning.runplans.html

**Conversion category:** Assisted (★★ — two-star feature compatibility)
**SCT automation:** N/A

Key differences: Syntax differences. Completely different optimizer with different operators and rules.

## Oracle

Run plans represent the choices made by the query optimizer for accessing data. Oracle generates run plans for `SELECT`, `INSERT`, `UPDATE`, and `DELETE` statements. They are displayed as a structured tree containing:

- Tables accessed and the referenced order for each.
- Access method per table (e.g., full table scan or index access).
- Join algorithms (e.g., hash or nested loop joins).
- Operations on retrieved data (filtering, sorting, aggregations).
- Rows being processed (cardinality) and the cost per operation.
- Table partitions accessed.
- Parallel run information.

Oracle 19 introduces **SQL Quarantine**: queries that consume resources excessively can be automatically quarantined and prevented from running.

Review a potential run plan with `EXPLAIN PLAN` / `SET AUTOTRACE TRACEONLY EXPLAIN` (shows the plan without running the query):

```sql
SET AUTOTRACE TRACEONLY EXPLAIN
SELECT EMPLOYEE_ID, LAST_NAME, FIRST_NAME FROM EMPLOYEES
WHERE LAST_NAME='King' AND FIRST_NAME='Steven';

-- Plan hash value: 2077747057
-- | Id | Operation                   | Name        | Rows | Bytes | Cost (%CPU) | Time
-- | 0  | SELECT STATEMENT            |             | 1    | 16    | 2 (0)       | 00:00:01
-- | 1  | TABLE ACCESS BY INDEX ROWID | EMPLOYEES   | 1    | 16    | 2 (0)       | 00:00:01
-- |* 2 | INDEX RANGE SCAN            | EMP_NAME_IX | 1    |       | 1 (0)       | 00:00:01
--
-- Predicate Information (identified by operation id):
-- 2 - access("LAST_NAME"='King' AND "FIRST_NAME"='Steven')
```

A plan showing a `FULL TABLE SCAN`:

```sql
SET AUTOTRACE TRACEONLY EXPLAIN
SELECT EMPLOYEE_ID, LAST_NAME, FIRST_NAME FROM EMPLOYEES
WHERE SALARY > 10000;

-- Plan hash value: 1445457117
-- | Id | Operation         | Name      | Rows | Bytes | Cost (%CPU) | Time
-- | 0  | SELECT STATEMENT  |           | 72   | 1368  | 3 (0)       | 00:00:01
-- |* 1 | TABLE ACCESS FULL | EMPLOYEES | 72   | 1368  | 3 (0)       | 00:00:01
--
-- Predicate Information (identified by operation id):
-- 1 - filter("SALARY">10000)
```

## MySQL

Aurora MySQL provides the `EXPLAIN` / `DESCRIBE` statement — usable with `SELECT`, `DELETE`, `INSERT`, `REPLACE`, and `UPDATE`. It can also retrieve table and column metadata.

- `EXPLAIN ... FOR CONNECTION <id>` returns the run plan for a statement running in a named connection.
- The `FORMAT` option selects `TRADITIONAL` tabular format or `JSON`.
- Requires `SELECT` permission for all tables/views accessed; for views also requires `SHOW VIEW`.
- MySQL Workbench provides a visual explain feature (similar to Oracle OEM graphical plans).
- RDS for MySQL 8.0.18+ implements `EXPLAIN ANALYZE`, giving expanded run information in `TREE` format (startup cost, total cost, rows returned, loops executed) — comparing estimated vs. actual cost. MySQL 8.0.21+ supports the `FORMAT=TREE` specifier (`TREE` is the only supported format).

### Syntax

```sql
{EXPLAIN | DESCRIBE | DESC} [EXTENDED | FORMAT = TRADITIONAL | JSON]
[SELECT statement | DELETE statement | INSERT statement | REPLACE statement | UPDATE
statement | FOR CONNECTION <connection id>]
```

### Examples

```sql
CREATE TABLE Employees (
    EmployeeID INT NOT NULL PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    INDEX USING BTREE(Name));

EXPLAIN SELECT * FROM Employees WHERE Name = 'Jason';

-- id  select_type  table      partitions  type  possible_keys  key   key_len ref    rows  Extra
-- 1   SIMPLE       Employees              ref   Name           Name  102     const  1
```

To force a join order matching the order tables are specified in a `SELECT`, use `SELECT STRAIGHT_JOIN`.

## Conversion notes

- The two engines use **completely different optimizers** with different operators and rules — plan output is not directly comparable; only the conceptual purpose maps over.
- Oracle uses `SET AUTOTRACE TRACEONLY EXPLAIN` / `EXPLAIN PLAN`; MySQL uses `EXPLAIN` / `DESCRIBE` / `DESC`.
- Oracle presents a structured tree with cost/cardinality columns; MySQL's traditional output is a flat row set (`id`, `select_type`, `table`, `type`, `possible_keys`, `key`, `rows`, `Extra`, etc.) or JSON/TREE format.
- MySQL adds `EXPLAIN ANALYZE` (8.0.18+) to compare estimated vs. actual cost — analogous to Oracle's actual-execution statistics.
- Use `STRAIGHT_JOIN` in MySQL to force join order, comparable to ordering/join hints in Oracle.
