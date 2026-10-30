# Database Hints

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tuning.dbhints.html

**Conversion category:** Assisted (★★ — two-star feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected MAX_EXECUTION_TIME (milliseconds, per statement — verified); added MySQL 8 join-order, index, hash-join, merge and SET_VAR hints (all verified on 3 / 8.4), silent ignore of bad hints, no plan baselines on Aurora MySQL.

Key differences: Very limited set of hints in MySQL. Use index hints and optimizer hints as comments. Syntax differences.

## Oracle

Oracle lets users influence the query optimizer's run-plan decisions via database hints — directives to the optimizer. Oracle supports over 60 hints (optimizer hints, join order hints, parallel run hints), each taking 0 or more arguments. Hints are embedded directly after the `SELECT` keyword using the format `/* <DB_HINT> */`.

Force the optimizer to use a specific index:

```sql
SELECT /* INDEX(EMP, IDX_EMP_HIRE_DATE)*/ * FROM EMPLOYEES EMP
WHERE HIRE_DATE >= '01-JAN-2010';

-- Run Plan
-- Plan hash value: 3035503638
-- | Id | Operation                   | Name          | Rows | Bytes | Cost (%CPU) | Time
-- | 0  | SELECT STATEMENT            |               | 1    | 62    | 2 (0)       | 00:00:01
-- | 1  | TABLE ACCESS BY INDEX ROWID | EMPLOYEES     | 1    | 62    | 2 (0)       | 00:00:01
-- |* 2 | INDEX RANGE SCAN            | IDX_HIRE_DATE | 1    |       | 1 (0)       | 00:00:01
--
-- Predicate Information (identified by operation id):
-- 2 - access("HIRE_DATE">=TO_DATE(' 2010-01-01 00:00:00', 'syyyy-mm-dd hh24:mi:ss'))
```

## MySQL

Aurora MySQL supports two types of hints: **index hints** and **optimizer hints**.

### Index hints

- `USE INDEX` limits the optimizer's choice to a white-list of indexes.
- `IGNORE INDEX` black-lists indexes.
- `FORCE INDEX` is like `USE INDEX (index_list)` but strongly favors seek over scan.
- Hints use actual index names, not column names. Refer to the primary key with the keyword `PRIMARY` (in Aurora MySQL the primary key is the clustered index).
- `<Index List>` can be omitted for `USE INDEX` only — meaning *don't use any indexes* (equivalent to a clustered index scan).
- Scope a hint with `FOR JOIN`, `FOR ORDER BY`, or `FOR GROUP BY`. Multiple hints may be specified.

```sql
SELECT ...
FROM <Table Name>
    USE {INDEX|KEY}
        [FOR {JOIN|ORDER BY|GROUP BY}] (<Index List>)
    | IGNORE {INDEX|KEY}
        [FOR {JOIN|ORDER BY|GROUP BY}] (<Index List>)
    | FORCE {INDEX|KEY}
        [FOR {JOIN|ORDER BY|GROUP BY}] (<Index List>)
...n
```

### Optimizer hints

Specified within the statement as a comment with the `+` prefix: `/*+ <Optimizer Hints> */`. Valid in one or two scopes (Global, Query-level, Table-level, Index-level).

```sql
SELECT /*+ <Optimizer Hints> */ <Select List>...
INSERT /*+ <Optimizer Hints> */ INTO <Table>...
REPLACE /*+ <Optimizer Hints> */ INTO <Table>...
UPDATE /*+ <Optimizer Hints> */ <Table> SET...
DELETE /*+ <Optimizer Hints> */ FROM <Table>...
```

Available optimizer hints:

| Hint Name | Description | Applicable Scopes |
|---|---|---|
| `BKA`, `NO_BKA` | Turn on/off batched key access join processing | Query block, table |
| `BNL`, `NO_BNL` | Turn on/off block nested loop join processing | Query block, table |
| `MAX_EXECUTION_TIME(ms)` | Limits a read-only `SELECT`'s run time in **milliseconds** for that statement (verified: `MAX_EXECUTION_TIME(1)` interrupted `SLEEP(1)`, which then returns 1). The original said seconds/global | Global (statement) |
| `MRR`, `NO_MRR` | Turn on/off multi-range read optimization | Table, index |
| `NO_ICP` | Turn off index condition push-down optimization | Table, index |
| `NO_RANGE_OPTIMIZATION` | Turn off range optimization | Table, index |
| `QB_NAME` | Assigns a logical name to a query block | Query block |
| `SEMIJOIN`, `NO_SEMIJOIN` | Turn on/off semi-join strategies | Query block |
| `SUBQUERY` | Determines `MATERIALIZATION` and `INTOEXISTS` processing | Query block |
| `JOIN_ORDER`, `JOIN_PREFIX`, `JOIN_SUFFIX`, `JOIN_FIXED_ORDER` | Join order (≈ Oracle `LEADING`/`ORDERED`) | Query block |
| `INDEX`, `NO_INDEX`, `JOIN_INDEX`, `GROUP_INDEX`, `ORDER_INDEX`, `INDEX_MERGE`, `SKIP_SCAN` | Index choice (≈ Oracle `INDEX`, `NO_INDEX`, `INDEX_SS`) | Table, index |
| `HASH_JOIN`, `NO_HASH_JOIN` (or `BNL`/`NO_BNL`, which control hash joins since 8.0.20) | Hash join on/off (≈ `USE_HASH`) | Query block, table |
| `MERGE`, `NO_MERGE` | Derived-table / view merging (≈ Oracle `MERGE`/`NO_MERGE`) | Table |
| `SET_VAR(var = value)` | Session variable for one statement (≈ `OPT_PARAM`) | Global |

All of the added hints were accepted on Aurora MySQL 3.13 and 8.4.8 (verified).

Use `QB_NAME` to name a query block, then reference it with `@` to scope a hint to named subqueries:

```sql
SELECT /*+ SEMIJOIN(@SubQuery1 FIRSTMATCH, LOOSESCAN) */ *
FROM Table1
WHERE Col1 IN (SELECT /*+ QB_NAME(SubQuery1) */ Col1
    FROM t3);
```

### Examples

```sql
-- Force an index access
SELECT * FROM Table1 USE INDEX (Index1) ORDER BY Col1;

-- Multiple index hints
SELECT * FROM Table1
    USE INDEX (Index1)
    INNER JOIN Table2
        IGNORE INDEX(Index2)
        ON Table1.Col1 = Table2.Col1
    ORDER BY Col1;

-- Optimizer hints
SELECT /*+ NO_RANGE_OPTIMIZATION(Table1 PRIMARY, Index2) */
Col1 FROM Table1 WHERE Col2 = 300;

SELECT /*+ BKA(t1) NO_BKA(t2) */ * FROM Table1 INNER JOIN Table2 ON ...;

SELECT /*+ NO_ICP(t1, t2) */ * FROM Table1 INNER JOIN Table2 ON ...;
```

## Conversion notes

- The Aurora MySQL hint framework is far more limited than Oracle's granular control. **Recommendation:** start migration testing with all hints removed, then selectively apply hints only as a last resort after schema, index, and query optimizations have failed.
- Aurora MySQL uses index lists with both white-list (`USE`) and black-list (`IGNORE`) semantics, versus Oracle's explicit single-index approach.
- Index hints are **not mandatory** — Aurora MySQL may choose alternatives if it cannot use the hinted index.
- `MAX_EXECUTION_TIME(ms)` applies to the statement it is in (or `SET SESSION max_execution_time = ms`); it affects read-only `SELECT`s only.
- Unknown or malformed hints are ignored with a warning, not an error — the same as Oracle — so a mistranslated hint silently does nothing. Check `SHOW WARNINGS` after `EXPLAIN`.
- There is no plan-baseline facility on Aurora MySQL (no SPM, no Aurora QPM — that is Aurora PostgreSQL only). Pin plans with hints in the SQL text, or with `optimizer_switch` per session.

### Feature mapping (Oracle → Aurora MySQL)

| Feature | Oracle | Aurora MySQL |
|---|---|---|
| Force a specific plan | `DBMS_SPM` | N/A |
| Join hints | `USE_NL`, `NO_USE_NL`, `USE_NL_WITH_INDEX`, `USE_MERGE`, `NO_USE_MERGE`, `USE_HASH`, `NO_USE_HASH`, `LEADING`, `ORDERED` | `HASH_JOIN`/`NO_HASH_JOIN` (`BNL`/`NO_BNL`), `BKA`, `JOIN_ORDER`/`JOIN_PREFIX`/`JOIN_FIXED_ORDER`; no sort-merge join |
| Force scan | `FULL` | `USE` with no index list forces a clustered index scan |
| Force an index | `INDEX` | `INDEX(t idx)` optimizer hint or `FORCE INDEX (idx)` |
| Allow/deny list indexes | `NO_INDEX` | Supported with `USE` and `IGNORE` |
| Parameter value hints | `opt_param` | `SET_VAR(...)` |
| Parallel query hints | `PARALLEL`, `NO_PARALLEL` | Aurora Parallel Query is cost-based; force per session with `aurora_pq_force` (test only) |
