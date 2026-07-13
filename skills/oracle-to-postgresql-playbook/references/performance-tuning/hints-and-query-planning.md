# Oracle Database Hints and PostgreSQL Query Planning

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tuning.hints.html

**Conversion category:** Manual
**SCT automation:** N/A (two-star feature compatibility; very limited set of hints in PostgreSQL — index/optimizer hints as comments, syntax differences)

## Oracle

Oracle lets users influence the query optimizer's run-plan decisions using **database hints** — directives that alter how run plans are generated. Oracle supports over 60 different hints, each taking 0 or more arguments, divided into categories such as optimizer hints, join order hints, and parallel execution hints.

Hints are embedded directly into SQL queries immediately following the `SELECT` keyword using the format `/* <DB_HINT> */`.

Example — force the optimizer to use a specific index for data access:

```sql
SELECT /* INDEX(EMP, IDX_EMP_HIRE_DATE)*/ *
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

PostgreSQL does **not** support database hints to influence the query planner — you cannot influence how execution plans are generated from within SQL queries. Instead, **session parameters** (Query Planning Parameters) can influence optimizer behavior at the session level.

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

- Oracle's 60+ inline hints have no direct PostgreSQL equivalent — there is no per-statement hint mechanism in core PostgreSQL.
- Oracle hints are statement-scoped (embedded in the SQL after `SELECT`); PostgreSQL planning parameters are session-scoped (`SET ...`), affecting all subsequent queries in the session until reset.
- Migration of hinted Oracle queries is a manual effort: remove the inline hints and reproduce the intended behavior via session-level `ENABLE_*` toggles (e.g., `ENABLE_SEQSCAN`, `ENABLE_NESTLOOP`) and cost parameters (`SEQ_PAGE_COST`, `RANDOM_PAGE_COST`).
- `ENABLE_*` toggles only discourage (raise the cost of) a plan choice rather than strictly forbidding it; the planner may still choose the discouraged method.
- Prefer fixing root causes (accurate statistics via `ANALYZE`, appropriate indexes) over forcing plans, since PostgreSQL favors a cost-based planner without hint overrides.
