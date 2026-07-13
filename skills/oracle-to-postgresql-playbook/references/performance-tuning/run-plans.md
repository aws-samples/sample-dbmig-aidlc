# Oracle and PostgreSQL Run Plans

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tuning.plans.html

**Conversion category:** Manual
**SCT automation:** N/A (two-star feature compatibility; syntax differences, completely different optimizer with different operators and rules in PostgreSQL)

A run plan is the sequence of operations the database engine performs to execute a SQL statement.

## Oracle

The query optimizer generates run plans for `SELECT`, `INSERT`, `UPDATE`, and `DELETE`. Plans are useful for performance tuning (e.g., deciding whether new indexes are needed) and can be affected by data volumes, statistics, and instance parameters (global or session).

Run plans are displayed as a structured tree with:
* Tables accessed and their referenced order.
* Access method per table (full table scan vs. index access).
* Join algorithms (hash vs. nested loop joins).
* Operations on retrieved data (filtering, sorting, aggregations).
* Rows processed (cardinality) and cost per operation.
* Table partitions accessed.
* Parallel run information.

Oracle 19 introduces **SQL Quarantine**: queries that consume resources excessively can be automatically quarantined and prevented from executing; their run plans are also quarantined.

Example — review the potential plan with `EXPLAIN PLAN` / `SET AUTOTRACE TRACEONLY EXPLAIN` (shows the plan without running the query):

```sql
SET AUTOTRACE TRACEONLY EXPLAIN
SELECT EMPLOYEE_ID, LAST_NAME, FIRST_NAME FROM EMPLOYEES
WHERE LAST_NAME='King' AND FIRST_NAME='Steven';

Run Plan
Plan hash value: 2077747057
Id  Operation                    Name         Rows  Bytes  Cost (%CPU)  Time
0   SELECT STATEMENT                          1     16     2 (0)        00:00:01
1   TABLE ACCESS BY INDEX ROWID  EMPLOYEES    1     16     2 (0)        00:00:01
2   INDEX RANGE SCAN             EMP_NAME_IX  1            1 (0)        00:00:01

Predicate Information (identified by operation id):
2 - access("LAST_NAME"='King' AND "FIRST_NAME"='Steven')
```

Step 2 shows an `INDEX RANGE SCAN` because indexes exist on both columns. A query without a usable index shows a `FULL TABLE SCAN`:

```sql
SET AUTOTRACE TRACEONLY EXPLAIN
SELECT EMPLOYEE_ID, LAST_NAME, FIRST_NAME FROM EMPLOYEES
WHERE SALARY > 10000;

Run Plan
Plan hash value: 1445457117
Id  Operation          Name         Rows  Bytes  Cost (%CPU)  Time
0   SELECT STATEMENT                72    1368   3 (0)        00:00:01
1   TABLE ACCESS FULL  EMPLOYEES    72    1368   3 (0)        00:00:01

Predicate Information (identified by operation id):
1 - filter("SALARY">10000)
```

See *Explaining and Displaying Execution Plans* in the Oracle documentation.

## PostgreSQL

The PostgreSQL equivalent of Oracle `EXPLAIN PLAN` is the `EXPLAIN` keyword, which displays the run plan for a SQL statement. Like Oracle, the planner generates estimated plans for `SELECT`, `INSERT`, `UPDATE`, and `DELETE`, building a structured tree of plan nodes (the `→` sign represents a root line in a PostgreSQL plan). `EXPLAIN` reports cost, rows, time, and loops per action.

Plain `EXPLAIN` does **not** run the statement (estimate only). `EXPLAIN ANALYZE` **runs** the statement in addition to displaying the plan.

Synopsis:

```sql
EXPLAIN [ ( option value[, ...] ) ] statement
EXPLAIN [ ANALYZE ] [ VERBOSE ] statement

where option and values can be one of:

  ANALYZE [ boolean ]
  VERBOSE [ boolean ]
  COSTS [ boolean ]
  BUFFERS [ boolean ]
  TIMING [ boolean ]
  SUMMARY [ boolean ] (since PostgreSQL 10)
  FORMAT { TEXT | XML | JSON | YAML }
```

By default, planning and run time are shown with `EXPLAIN ANALYZE` but not otherwise; the `SUMMARY` option gives explicit control to include planning/run-time metrics.

PostgreSQL can cancel statements running longer than a limit via the instance-level `statement_timeout` parameter. If specified without units it is milliseconds; zero (default) disables the timeout. Third-party connection poolers such as `Pgbouncer` and `PgPool` add more flexibility over how long a connection can run or stay idle.

Example — view the estimated plan:

```sql
EXPLAIN
  SELECT EMPLOYEE_ID, LAST_NAME, FIRST_NAME FROM EMPLOYEES
  WHERE LAST_NAME='King' AND FIRST_NAME='Steven';

Index Scan using idx_emp_name on employees (cost=0.14..8.16 rows=1 width=18)
Index Cond: (((last_name)::text = 'King'::text) AND ((first_name)::text = 'Steven'::text))
(2 rows)
```

Run the same statement with `ANALYZE` for actual execution metrics:

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

A full table scan appears as a `Seq Scan`:

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

PostgreSQL scan types include sequential scans, index scans, and bitmap index scans. The sequential scan (`Seq Scan`) is the PostgreSQL equivalent of Oracle `TABLE ACCESS FULL`.

### Aurora PostgreSQL Query Plan Management (QPM)

Aurora PostgreSQL QPM addresses plan instability, letting users maintain stable yet optimal performance for a set of managed SQL statements. Two main objectives:
* **Plan stability** — prevents plan regression and improves stability when system changes occur.
* **Plan adaptability** — automatically detects new minimum-cost plans and controls when new plans may be used.

Changes in statistics, constraints, environment settings, query parameter bindings, and software upgrades can all cause the optimizer to pick a different plan and lead to performance regression. With QPM you can:
* Improve plan stability by forcing the optimizer to choose from a small number of known, good plans.
* Optimize plans centrally and distribute the best plans globally.
* Identify unused indexes and assess the impact of creating or dropping an index.
* Automatically detect a new minimum-cost plan discovered by the optimizer.
* Try new optimizer features with less risk by approving only plan changes that improve performance.

See *EXPLAIN* in the PostgreSQL documentation.

## Conversion notes

- Oracle and PostgreSQL use completely different optimizers with different operators and rules; plan output formats and operator names differ.
- Operator mapping: Oracle `TABLE ACCESS FULL` → PostgreSQL `Seq Scan`; `TABLE ACCESS BY INDEX ROWID` / `INDEX RANGE SCAN` → `Index Scan` (also `Bitmap Index Scan`).
- `EXPLAIN PLAN` / `SET AUTOTRACE TRACEONLY EXPLAIN` (estimate-only) maps to PostgreSQL `EXPLAIN` (estimate-only). To actually execute and get real timings/cardinality, use `EXPLAIN ANALYZE` (Oracle has no exact equivalent in this estimate-only mode).
- Use `EXPLAIN ANALYZE` cautiously: it runs the statement, so it modifies data for DML — wrap in a transaction and roll back if needed.
- Use `VERBOSE`, `BUFFERS`, and `SUMMARY` options for richer diagnostics; `FORMAT JSON`/`YAML`/`XML` is useful for tooling.
- For plan-stability concerns equivalent to Oracle SQL Plan Baselines/Quarantine, use Aurora PostgreSQL **Query Plan Management (QPM)**.
- Control long-running statements with `statement_timeout` (instance-level), optionally augmented by connection poolers (`Pgbouncer`, `PgPool`).
