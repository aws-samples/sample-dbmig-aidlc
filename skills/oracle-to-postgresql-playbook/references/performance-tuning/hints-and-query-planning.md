# Oracle Database Hints and PostgreSQL Query Planning

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tuning.hints.html

**Conversion category:** Manual
**SCT automation:** N/A (two-star feature compatibility; very limited set of hints in PostgreSQL — index/optimizer hints as comments, syntax differences)

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): added `pg_hint_plan` (verified) and QPM as hint options, an Oracle→`pg_hint_plan` mapping, and fixed Oracle hint syntax (`/*+ */`).

## Oracle

Oracle lets users influence the query optimizer's run-plan decisions using **database hints** — directives that alter how run plans are generated. Oracle supports over 60 different hints, each taking 0 or more arguments, divided into categories such as optimizer hints, join order hints, and parallel execution hints.

Hints are embedded directly into SQL queries immediately following the `SELECT` keyword using the format `/*+ <DB_HINT> */` (the `+` is required; a plain comment is ignored).

Example — force the optimizer to use a specific index for data access:

```sql
SELECT /*+ INDEX(EMP, IDX_EMP_HIRE_DATE) */ *
  FROM EMPLOYEES EMP
  WHERE HIRE_DATE >= '01-JAN-2010';

Run Plan
Plan hash value: 3035503638
Id  Operation                    Name           Rows  Bytes  Cost (%CPU)  Time
0   SELECT STATEMENT                            1     62     2 (0)        00:00:01
1   TABLE ACCESS BY INDEX ROWID  EMPLOYEES      1     62     2 (0)        00:00:01
2   INDEX RANGE SCAN             IDX_HIRE_DATE  1            1 (0)        00:00:01

Predicate Information (identified by operation id):
2 - access("HIRE_DATE">=TO_DATE(' 2010-01-01 00:00:00', 'yyyy-mm-dd hh24:mi:ss'))
```

See *Comments* and *Influencing the Optimizer* in the Oracle documentation.

## PostgreSQL

Core PostgreSQL does **not** support inline hints. On Aurora PostgreSQL 18 there are three options, in this order of preference:

1. **Fix the root cause**: statistics (`ANALYZE`, extended statistics), indexes, and query shape. Most Oracle hints exist to work around Oracle optimizer behavior and are not needed in PostgreSQL.
2. **Aurora Query Plan Management (QPM, `apg_plan_mgmt`)**: capture and approve plans centrally, without changing SQL text. This is the equivalent of Oracle SQL Plan Baselines. See `run-plans.md`.
3. **`pg_hint_plan`** (1.8.0 on Aurora 18; add it to `shared_preload_libraries`, then `CREATE EXTENSION pg_hint_plan`): Oracle-style `/*+ … */` comment hints. Verified on 18.6:

```sql
/*+ IndexScan(e idx_emp_hire_date) */ SELECT * FROM employees e WHERE hire_date >= DATE '2010-01-01';
/*+ SeqScan(e) */ SELECT ...;
/*+ HashJoin(e d) Leading((e d)) */ SELECT ... FROM employees e JOIN departments d USING (department_id);
/*+ Set(enable_nestloop off) */ SELECT ...;   -- statement-scoped planner setting
```

Common Oracle → `pg_hint_plan` mapping: `INDEX(t i)` → `IndexScan(t i)`; `FULL(t)` → `SeqScan(t)`; `USE_HASH(a b)` → `HashJoin(a b)`; `USE_NL(a b)` → `NestLoop(a b)`; `USE_MERGE` → `MergeJoin`; `LEADING(a b c)` → `Leading(a b c)`; `PARALLEL(t n)` → `Parallel(t n)`; `CARDINALITY` → `Rows(a b #n)`. Hints such as `FIRST_ROWS`, `APPEND`, `RESULT_CACHE`, and `NO_MERGE` have no `pg_hint_plan` equivalent; drop them. In `pg_hint_plan` the hint comment must come **first** in the statement (before `SELECT`), unlike Oracle.

**Session parameters** (Query Planning Parameters) can also influence optimizer behavior at the session level:

Set the planner to use indexes instead of full table scans (disable `SEQSCAN`):

```sql
SET ENABLE_SEQSCAN=FALSE;
```

Set the estimated cost of a sequential disk-page fetch (`SEQ_PAGE_COST`) and the cost of a non-sequentially-fetched disk page (`RANDOM_PAGE_COST`). Reducing `RANDOM_PAGE_COST` relative to `SEQ_PAGE_COST` makes the planner prefer index scans; raising it makes index scans more expensive:

```sql
SET SEQ_PAGE_COST to 4;
SET RANDOM_PAGE_COST to 1;
```

Discourage the planner from using nested-loop joins. It cannot be fully disabled, but setting `ENABLE_NESTLOOP` to `OFF` discourages it relative to alternative join methods:

```sql
SET ENABLE_NESTLOOP to FALSE;
```

See *Query Planning* in the PostgreSQL documentation.

## Conversion notes

- Oracle's 60+ inline hints have no direct equivalent in core PostgreSQL. On Aurora, `pg_hint_plan` covers the common access-path, join-method, join-order and parallel hints. **Default conversion: drop hints** and record them in the conversion log. Re-add only the ones a performance test proves necessary, preferably as a QPM-approved plan.
- Oracle hints are statement-scoped (embedded in the SQL after `SELECT`); PostgreSQL planning parameters are session-scoped (`SET ...`), affecting all subsequent queries in the session until reset.
- Migration of hinted Oracle queries is a manual effort. When a hint is needed, prefer `pg_hint_plan` (statement-scoped) or `SET LOCAL` inside a transaction over session-wide `SET`, which leaks into later queries on pooled connections.
- `ENABLE_*` toggles only discourage (raise the cost of) a plan choice rather than strictly forbidding it; the planner may still choose the discouraged method.
- `random_page_cost`: Aurora storage is SSD-backed, so values close to `seq_page_cost` (for example `1.1`) are a common starting point instead of the default `4`. Measure before changing it cluster-wide.
- Prefer fixing root causes (accurate statistics via `ANALYZE`, appropriate indexes) over forcing plans, since PostgreSQL favors a cost-based planner without hint overrides.
