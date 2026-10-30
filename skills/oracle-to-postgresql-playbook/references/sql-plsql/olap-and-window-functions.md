# OLAP and Window Functions

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.olap.html

**Conversion category:** Assisted (Four-star feature compatibility, four-star automation; `GREATEST`/`LEAST` may differ; `CONNECT BY` not supported, workaround available)
**SCT automation:** Four-star automation level; SCT action code index → OLAP Functions

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PG 11–16 window/aggregate features (`GROUPS`, `EXCLUDE`, `FILTER`, `any_value`), Oracle `LISTAGG`/`MEDIAN`/`KEEP`/`RATIO_TO_REPORT`/`CONNECT BY LEVEL` rewrites (verified), GREATEST/LEAST NULL semantics.

## Oracle

Oracle OLAP functions extend standard SQL analytic functions, computing aggregate values over logically partitioned result sets within a single query. Commonly used for BI/reporting and can outperform equivalent non-OLAP SQL.

Common Oracle OLAP function types:

| Type | Related functions |
|---|---|
| Aggregate | `average_rank`, `avg`, `count`, `dense_rank`, `max`, `min`, `rank`, `sum` |
| Analytic | `average_rank`, `avg`, `count`, `dense_rank`, `lag`, `lag_variance`, `lead_variance_percent`, `max`, `min`, `rank`, `row_number`, `sum`, `percent_rank`, `cume_dist`, `ntile`, `first_value`, `last_value` |
| Hierarchical | `hier_ancestor`, `hier_child_count`, `hier_depth`, `hier_level`, `hier_order`, `hier_parent`, `hier_top` |
| Lag | `lag`, `lag_variance`, `lag_variance_percent`, `lead`, `lead_variance`, `lead_variance_percent` |
| OLAP DML | `olap_dml_expression` |
| Rank | `average_rank`, `dense_rank`, `rank`, `row_number` |

Example `RANK()`:

```sql
SELECT department_id, last_name, salary, commission_pct,
    RANK() OVER (PARTITION BY department_id
    ORDER BY salary DESC, commission_pct) "Rank"
FROM employees WHERE department_id = 80;

DEPARTMENT_ID LAST_NAME SALARY COMMISSION_PCT Rank
80            Russell   14000  .4             1
80            Partners  13500  .3             2
80            Errazuriz 12000  .3             3
```

## PostgreSQL

PostgreSQL calls ANSI SQL analytic functions **Window Functions**. They operate on a logical "partition"/"window" of the result set. Two main types: aggregation and ranking.

> Note: Even when functionality matches, the returned data type may differ and require application changes.

| Type | Related functions |
|---|---|
| Aggregate | `avg`, `count`, `max`, `min`, `sum`, `string_agg`, `array_agg`, `any_value` (PG 16), `bool_and/or`, `stddev*`, `var*`, `corr`, `regr_*` |
| Ordered-set | `percentile_cont`, `percentile_disc`, `mode` … `WITHIN GROUP (ORDER BY …)` |
| Ranking | `row_number`, `rank`, `dense_rank`, `percent_rank`, `cume_dist`, `ntile`, `lag`, `lead`, `first_value`, `last_value`, `nth_value` |

Frames support `ROWS`, `RANGE` (with offsets, PG 11+), `GROUPS`, and `EXCLUDE CURRENT ROW | GROUP | TIES`. Aggregates accept `FILTER (WHERE …)`. All of these are verified on 18.6.

**Oracle analytic constructs that need a rewrite** (verified on 18.6):

| Oracle | PostgreSQL |
|---|---|
| `LISTAGG(x, ',') WITHIN GROUP (ORDER BY y)` | `string_agg(x, ',' ORDER BY y)` (`LISTAGG … ON OVERFLOW` has no equivalent) |
| `MEDIAN(x)` | `percentile_cont(0.5) WITHIN GROUP (ORDER BY x)` |
| `RATIO_TO_REPORT(x) OVER ()` | `x / sum(x) OVER ()` |
| `MAX(x) KEEP (DENSE_RANK FIRST ORDER BY y)` | `(array_agg(x ORDER BY y))[1]` as an aggregate, or `first_value(x) OVER (… ORDER BY y)` |
| `SELECT LEVEL FROM DUAL CONNECT BY LEVEL <= n` (row generator) | `SELECT g FROM generate_series(1, n) g` |
| `STATS_MODE(x)` | `mode() WITHIN GROUP (ORDER BY x)` |
| `ANY_VALUE(x)` (Oracle 21c) | `any_value(x)` (PG 16+) |

Equivalent `RANK()` (identical syntax, different numeric formatting):

```sql
SELECT department_id, last_name, salary, commission_pct,
    RANK() OVER (PARTITION BY department_id
    ORDER BY salary DESC, commission_pct) "Rank"
FROM employees WHERE department_id = 80;

DEPARTMENT_ID LAST_NAME SALARY    COMMISSION_PCT Rank
80            Russell   14000.00  0.40           1
80            Partners  13500.00  0.30           2
80            Errazuriz 12000.00  0.30           3
```

### CONNECT BY equivalent in PostgreSQL

PostgreSQL has no `CONNECT BY`. Workarounds:
- `generate_series` function
- Recursive views / `WITH RECURSIVE`

```sql
SELECT "DATE"
FROM generate_series(timestamp '2010-01-01',
                     timestamp '2017-01-01',
                     interval '1 day') s("DATE");

DATE
---------------------
2010-01-01 00:00:00
2010-01-02 00:00:00
2010-01-03 00:00:00
…
```

### Extended analytics

For heavy OLAP/BI workloads against large datasets, consider Amazon Redshift (columnar store, MPP). Redshift window functions:

| Type | Functions |
|---|---|
| Aggregate | `AVG`, `COUNT`, `CUME_DIST`, `FIRST_VALUE`, `LAG`, `LAST_VALUE`, `LEAD`, `MAX`, `MEDIAN`, `MIN`, `NTH_VALUE`, `PERCENTILE_CONT`, `PERCENTILE_DISC`, `RATIO_TO_REPORT`, `STDDEV_POP`, `STDDEV_SAMP`, `SUM`, `VAR_POP`, `VAR_SAMP` |
| Ranking | `DENSE_RANK`, `NTILE`, `PERCENT_RANK`, `RANK`, `ROW_NUMBER` |

## Summary — Oracle OLAP vs PostgreSQL window functions (all compatible syntax: Yes)

| Oracle | Oracle return type | PostgreSQL | PG return type |
|---|---|---|---|
| `Count` | Number | `Count` | bigint |
| `Max` | Number | `Max` | numeric/string/date-time/network/enum |
| `Min` | Number | `Min` | numeric/string/date-time/network/enum |
| `Avg` | Number | `Avg` | numeric/double else arg type |
| `Sum` | Number | `Sum` | bigint else arg type |
| `rank()` | Number | `rank()` | bigint |
| `row_number()` | Number | `row_number()` | bigint |
| `dense_rank()` | Number | `dense_rank()` | bigint |
| `percent_rank()` | Number | `percent_rank()` | double |
| `cume_dist()` | Number | `cume_dist()` | double |
| `ntile()` | Number | `ntile()` | integer |
| `lag()` | Same as value | `lag()` | Same as value |
| `lead()` | Same as value | `lead()` | Same as value |
| `first_value()` | Same as value | `first_value()` | Same as value |
| `last_value()` | Same as value | `last_value()` | Same as value |

## Conversion notes

- Window function syntax (`OVER (PARTITION BY … ORDER BY …)`) is identical; standard ranking/aggregate window functions migrate directly.
- Watch for **return-type differences** (e.g., `bigint`, `double`) that may require application-side casting or formatting changes.
- `GREATEST`/`LEAST` ignore NULL arguments in PostgreSQL (`greatest(1, NULL) = 1`, verified) but return NULL in Oracle if any argument is NULL. Where Oracle's NULL result matters, add `CASE WHEN a IS NULL OR b IS NULL THEN NULL ELSE greatest(a,b) END`.
- Default NULL ordering matches Oracle (`ASC NULLS LAST`, `DESC NULLS FIRST`), so explicit `NULLS FIRST/LAST` clauses carry over unchanged.
- Numeric results: `sum`/`avg` over `numeric` return `numeric` with possibly many decimal digits (`x / sum(x)` gave 20 decimal places, verified). Round explicitly where Oracle output was compared textually.
- Rewrite Oracle hierarchical `CONNECT BY` queries using `WITH RECURSIVE` or `generate_series`.
- Oracle hierarchical OLAP functions (`hier_*`) have no PG window-function equivalent; redesign as recursive CTEs.
