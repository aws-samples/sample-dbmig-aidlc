# Tuning Run Plans

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tuning.plans.html

**Conversion category:** Manual (two-star feature compatibility)
**SCT automation:** N/A

Run plans provide detailed information about the data access and processing methods chosen by the query optimizer, including estimated or actual costs of each operator and sub-tree. SQL Server and PostgreSQL use completely different optimizers with different operators and rules, so plans are not directly portable — only the analysis technique transfers.

## SQL Server

SQL Server creates run plans for most queries and returns them to clients as plain text or XML. It can produce an estimated plan without running the query, or an actual plan after execution. SQL Server Management Studio renders the underlying XML plan graphically with icons and arrows.

SQL Server 2017+ adds automatic tuning, which detects query run-plan choice regressions and can apply corrective actions automatically or notify the user.

Estimated run plan:

```sql
SET SHOWPLAN_XML ON;
SELECT *
FROM MyTable
WHERE SomeColumn = 3;
SET SHOWPLAN_XML OFF;
```

Actual run plan (returns run-time statistics about resource usage and warnings after execution):

```sql
SET STATISTICS XML ON;
SELECT *
FROM MyTable
WHERE SomeColumn = 3;
SET STATISTICS XML OFF;
```

Other options: `SHOWPLAN_ALL`, `SHOWPLAN_TEXT` (estimated, text), and `STATISTICS PROFILE` (returns an extra result set with the run plan).

## PostgreSQL

Use `EXPLAIN` to generate the estimated run plan for `SELECT`, `INSERT`, `UPDATE`, and `DELETE`. It builds a structured tree of plan nodes (the `→` sign marks a root line) and reports cost, rows, time, and loops per node. `EXPLAIN` alone does not run the statement; `EXPLAIN ANALYZE` actually executes it and shows real timings.

Synopsis:

```sql
EXPLAIN [ ( option value[, ...] ) ] statement
EXPLAIN [ ANALYZE ] [ VERBOSE ] statement

where option can be one of:
  ANALYZE [ boolean ]
  VERBOSE [ boolean ]
  COSTS [ boolean ]
  BUFFERS [ boolean ]
  TIMING [ boolean ]
  SUMMARY [ boolean ]   -- since PostgreSQL 10
  FORMAT { TEXT | XML | JSON | YAML }
```

Estimated plan (index scan):

```sql
EXPLAIN
SELECT EMPLOYEE_ID, LAST_NAME, FIRST_NAME FROM EMPLOYEES
WHERE LAST_NAME='King' AND FIRST_NAME='Steven';

Index Scan using idx_emp_name on employees (cost=0.14..8.16 rows=1 width=18)
  Index Cond: (((last_name)::text = 'King'::text) AND ((first_name)::text = 'Steven'::text))
(2 rows)
```

Actual plan with `ANALYZE`:

```sql
EXPLAIN ANALYZE
SELECT EMPLOYEE_ID, LAST_NAME, FIRST_NAME FROM EMPLOYEES
WHERE LAST_NAME='King' AND FIRST_NAME='Steven';

Seq Scan on employees (cost=0.00..3.60 rows=1 width=18) (actual time=0.012..0.024 rows=1 loops=1)
  Filter: (((last_name)::text = 'King'::text) AND ((first_name)::text = 'Steven'::text))
  Rows Removed by Filter: 106
Planning time: 0.073 ms
Execution time: 0.037 ms
(5 rows)
```

Sequential scan (PostgreSQL equivalent of a SQL Server full table scan):

```sql
EXPLAIN ANALYZE
SELECT EMPLOYEE_ID, LAST_NAME, FIRST_NAME FROM EMPLOYEES
WHERE SALARY > 10000;

Seq Scan on employees (cost=0.00..3.34 rows=15 width=18) (actual time=0.012..0.036 rows=15 loops=1)
  Filter: (salary > '10000'::numeric)
  Rows Removed by Filter: 92
Planning time: 0.069 ms
Execution time: 0.052 ms
(5 rows)
```

PostgreSQL scan types: sequential scans, index scans, and bitmap index scans.

### Aurora PostgreSQL Query Plan Management (QPM)

Aurora PostgreSQL QPM addresses plan instability for a set of managed SQL statements:

- **Plan stability** — forces the optimizer to choose from a small number of known, good plans, preventing regression.
- **Plan adaptability** — automatically detects new minimum-cost plans and controls when they may be used.

QPM lets you optimize plans centrally and distribute them globally, identify unused indexes, assess index create/drop impact, and approve only plan changes that improve performance — useful when trying new optimizer features with less risk.

## Conversion notes

- Two-star (manual) feature compatibility: syntax differs and the optimizers are completely different, with different operators and rules. Plans do not translate directly.
- SQL Server `SET SHOWPLAN_XML`/`SHOWPLAN_TEXT`/`SHOWPLAN_ALL` (estimated) → PostgreSQL `EXPLAIN` (estimated, statement not run).
- SQL Server `SET STATISTICS XML`/`STATISTICS PROFILE` (actual) → PostgreSQL `EXPLAIN ANALYZE` (statement is executed).
- SQL Server full table scan ≈ PostgreSQL `Seq Scan`.
- SQL Server has graphical plans (SSMS) and built-in automatic tuning (2017+). PostgreSQL plans are textual (or XML/JSON/YAML via `FORMAT`); on Aurora, plan stability/regression control is provided by Query Plan Management (QPM) rather than an in-engine auto-tuner.
- PostgreSQL can cap long-running statements with the `statement_timeout` parameter (milliseconds if unitless; `0` disables). External poolers (PgBouncer, PgPool) add further connection/idle controls.
- Use `EXPLAIN (ANALYZE, BUFFERS)` and `SUMMARY` for richer diagnostics; `EXPLAIN ANALYZE` shows planning and execution time by default.
