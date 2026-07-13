# OLAP and Window Functions

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.olap.html

**Conversion category:** Assisted/Manual (★★★★ feature compatibility, ★★★★ automation)
**SCT automation:** N/A — `GREATEST`/`LEAST` may differ; `CONNECT BY` unsupported (workaround available).

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

Some Oracle OLAP functions are plain aggregate functions in Aurora MySQL. Others need window functions — **Aurora MySQL 5.7 does NOT support window functions.** (Amazon RDS for MySQL 8 supports them: `RANK()`, `LAG()`, `NTILE()`, plus aggregate-as-window `SUM()`, `AVG()`, etc.; MySQL 8 syntax is ANSI compliant.)

### Migration considerations
- Rewrite window-function logic with traditional SQL (correlated subqueries) — usually less optimal in performance/readability.
- Consider archiving the original code to reuse after upgrading to MySQL/Aurora 8.

```sql
CREATE TABLE OrderItems(
  OrderID INT NOT NULL, Item VARCHAR(20) NOT NULL, Quantity SMALLINT NOT NULL,
  PRIMARY KEY(OrderID, Item));
INSERT INTO OrderItems (OrderID, Item, Quantity)
  VALUES (1,'M8 Bolt',100),(2,'M8 Nut',100),(3,'M8 Washer',200);

-- Workaround for window ranking function (RANK)
SELECT Item, Quantity,
  (SELECT COUNT(*) FROM OrderItems AS OI2 WHERE OI.Quantity > OI2.Quantity) + 1 AS QtyRank
FROM OrderItems AS OI;

-- Workaround for partitioned window aggregate (SUM OVER PARTITION)
SELECT Item, Quantity,
  (SELECT SUM(Quantity) FROM OrderItems AS OI2 WHERE OI2.OrderID = OI.OrderID) AS TotalOrderQty
FROM OrderItems AS OI;
```

## Conversion notes
- Oracle aggregate-style OLAP functions (`AVG`, `COUNT`, `MAX`, `MIN`, `SUM`) map to MySQL aggregates directly.
- True window/analytic functions (`RANK`, `ROW_NUMBER`, `LAG`, `LEAD`, `NTILE`, `FIRST_VALUE`, `LAST_VALUE`, `CUME_DIST`, `PERCENT_RANK`) require correlated-subquery rewrites on Aurora MySQL 5.7.
- `CONNECT BY` hierarchical queries are unsupported — use the recursive workaround (loop in stored procedure).
- `GREATEST`/`LEAST` may return different results in MySQL — verify.
- If targeting MySQL 8, native window functions are available — no rewrite needed.
