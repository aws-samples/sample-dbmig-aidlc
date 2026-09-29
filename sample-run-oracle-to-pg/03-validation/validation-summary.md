# Validation summary — DEMO → demo

| Check | Result |
|---|---|
| Data load (`migrate-data`) | 199 rows, 14 tables |
| Reconcile (`compare`) | **14/14** tables match |
| Equivalence tests (`run-tests`) | **53/53** pass, first run (15 objects; per-case `type` lets package specs mix function + procedure cases) |
| Identity (`reset-identity`) | 12/12 identity columns safe (next > MAX) |
| Open follow-ups | 0 |

Write paths proven with real deltas (not trivial passes): `inventory_pkg_reduce_inventory` qty −3;
`order_pkg` create + add item → total +21.90; `update_order_status('SHIPPED')` sets only `shipped_date`;
`reporting_pkg_get_top_books` executed on populated rows (2 rows, sold 3).

**LOW_COVERAGE** (every table read is empty in the source — only the empty/default path ran):
`get_customer_lifetime_value`, `archive_old_orders`, `clear_shopping_cart`, `generate_sales_report`.
**Manual review:** the 4 procedures that COMMIT in Oracle were tested with non-existent keys only;
error paths (`Insufficient inventory`, invalid action) are not compared by the harness.

## Carry-forward for the application team
1. `NUMBER(1)` flags are `smallint` 0/1 — Boolean mappings need `@JdbcTypeCode(SqlTypes.SMALLINT)`.
2. `DATE` columns are `timestamp(0)` — `LocalDate` mappings need `@JdbcTypeCode(SqlTypes.TIMESTAMP)`.
3. `BLOB` → `bytea` — drop `@Lob`, use `@JdbcTypeCode(SqlTypes.VARBINARY)`.
4. `fulltext_redesign`: rewrite `CONTAINS/SCORE` to the `to_tsvector('english', coalesce(search_text,''))` expression.
5. Packages flattened (names above); error codes `U0001`/`U0002` (SQLSTATE).
6. Untested on real data (LOW_COVERAGE): the order/cart paths.
