# OLAP and Window Functions

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.olap.html

**Conversion category:** Assisted/Manual (★★★★ feature compatibility, ★★★★ automation)
**SCT automation:** N/A — `GREATEST`/`LEAST` may differ; `CONNECT BY` unsupported (workaround available).

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Window functions are native on 3 / 8.4 (verified); added the verified gap list (IGNORE NULLS error 1235, no PERCENTILE/MEDIAN, RATIO_TO_REPORT, LISTAGG→GROUP_CONCAT, RANGE INTERVAL rule, no GROUPING SETS); corrected the GREATEST note; 5.7 workarounds marked legacy.

## Oracle

OLAP (analytic) functions compute aggregate values over logically partitioned row sets within a single query — useful for BI/analytics and often faster than equivalent non-OLAP SQL.

Common Oracle OLAP function groups:

| Type | Functions |
|---|---|
| Aggregate | `average_rank`, `avg`, `count`, `dense_rank`, `max`, `min`, `rank`, `sum` |
| Analytic | `average_rank`, `avg`, `count`, `dense_rank`, `lag`, `lag_variance`, `lead_variance_percent`, `max`, `min`, `rank`, `row_number`, `sum`, `percent_rank`, `cume_dist`, `ntile`, `first_value`, `last_value` |
| Hierarchical | `hier_ancestor`, `hier_child_count`, `hier_depth`, `hier_level`, `hier_order`, `hier_parent`, `hier_top` |
| Lag | `lag`, `lag_variance`, `lag_variance_percent`, `lead`, `lead_variance`, `lead_variance_percent` |
| OLAP DML | `olap_dml_expression` |
| Rank | `average_rank`, `dense_rank`, `rank`, `row_number` |

## MySQL

**Aurora MySQL 3 and 8.4 support SQL-standard window functions** (verified on 3.13.0 and 8.4.8): `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `NTILE`, `PERCENT_RANK`, `CUME_DIST`, `LAG`, `LEAD`, `FIRST_VALUE`, `LAST_VALUE`, `NTH_VALUE`, and aggregates (`SUM`, `AVG`, `COUNT`, `MIN`, `MAX`, `BIT_*`, `JSON_ARRAYAGG`, `STD`/`VARIANCE`) with `OVER (PARTITION BY … ORDER BY … ROWS|RANGE …)`, plus named windows (`WINDOW w AS (…)`). Most Oracle analytic SQL converts unchanged.

```sql
SELECT item, quantity,
       RANK() OVER (ORDER BY quantity DESC)                    AS qty_rank,
       SUM(quantity) OVER (PARTITION BY order_id)              AS total_order_qty,
       LAG(item, 1, 'none') OVER (ORDER BY item)               AS prev_item,
       quantity / SUM(quantity) OVER (PARTITION BY order_id)   AS ratio_to_report
FROM order_items;
```

Gaps on both versions (verified):

| Oracle | MySQL 3 / 8.4 | Rewrite |
|---|---|---|
| `IGNORE NULLS` in `FIRST_VALUE`/`LAST_VALUE`/`LAG`/`LEAD` | error 1235 "doesn't yet support 'IGNORE NULLS'" | `MAX(col) OVER (…)` over a running group, or a correlated subquery |
| `PERCENTILE_CONT` / `PERCENTILE_DISC` / `MEDIAN` | not available (syntax error / no function) | `ROW_NUMBER()` + `COUNT() OVER` and pick/average the middle rows |
| `RATIO_TO_REPORT(x)` | not available | `x / SUM(x) OVER (PARTITION BY …)` |
| `LISTAGG … WITHIN GROUP` | aggregate only | `GROUP_CONCAT(x ORDER BY … SEPARATOR ',')` (not a window function; raise `group_concat_max_len`, default 1024) |
| `KEEP (DENSE_RANK FIRST/LAST)` | not available | `FIRST_VALUE … OVER` in a derived table, or `ROW_NUMBER() = 1` |
| `RANGE BETWEEN INTERVAL … PRECEDING` | allowed only with one numeric/temporal `ORDER BY` key (error 3587 otherwise) | same rule as Oracle; order by the date column |
| `GROUPING SETS` / `CUBE` | not available; `WITH ROLLUP` + `GROUPING()` only | `UNION ALL` of the grouping levels |
| `MODEL` clause | not available | procedural rewrite |

## Conversion notes
- Oracle aggregate-style OLAP functions (`AVG`, `COUNT`, `MAX`, `MIN`, `SUM`) map to MySQL aggregates directly; analytic functions map to native window functions on Aurora MySQL 3 / 8.4.
- `CONNECT BY` → `WITH RECURSIVE` (see `common-table-expressions.md`).
- `GREATEST`/`LEAST` return NULL if any argument is NULL in both engines (verified: `GREATEST(1, NULL, 3)` → NULL), but MySQL compares mixed types differently (string vs number); cast arguments to one type.
- Window functions cannot be used in `WHERE`, `GROUP BY` or `HAVING`; wrap the query in a derived table or CTE to filter on them (same as Oracle).
- Legacy (Aurora MySQL 5.7 only): correlated-subquery rewrites such as `(SELECT COUNT(*) FROM t t2 WHERE t.q > t2.q) + 1` for `RANK()`. Do not use them on 3 / 8.4.
