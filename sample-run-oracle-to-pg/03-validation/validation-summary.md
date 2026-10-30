# Validation summary — DEMO → demo (Aurora PostgreSQL 18.6)

| Check | Result |
|---|---|
| Data load (`migrate-data`) | 199 rows, 14 tables |
| Post-data (FKs + trigger) | **7/7** applied |
| Reconcile (`compare`) | **14/14** tables match (row count + column checksums) |
| Equivalence tests (`run-tests`) | **58/58** on the first run, 15 objects |
| Identity (`reset-identity`) | **12/12** identity columns safe |

**Write paths proven with real deltas** (rolled back on both engines): `inventory_pkg_reduce_inventory`
(listing quantity −2), `order_pkg_create_order`, `order_pkg_add_order_item` (order total 21.90),
`order_pkg_update_order_status` (only `shipped_date` set), and `reporting_pkg_get_top_books` executed over
an order created in the test transaction (row count, `total_sold`, `revenue`).

**Target behavior differences covered** (from the PG 18 baseline injected into `_context-tests.md`):
empty string vs NULL (`validation_pkg` v3, v7), `REGEXP_REPLACE` all-matches (v6), `NO_DATA_FOUND` with
`INTO STRICT` and from SQL (`get_*_name` c3, `inventory_pkg` i4), set-returning column types executed (r1–r3),
rounding (`calculate_discount_pct` c3, c4).

**LOW_COVERAGE** (source tables empty — only the empty/default path ran): `get_customer_lifetime_value`,
`archive_old_orders`, `clear_shopping_cart`, `generate_sales_report`.

**Manual review:** the 4 procedures that `COMMIT` in the source (`archive_old_orders`, `clear_shopping_cart`,
`process_customer_offer`, `set_book_featured`) were tested with non-destructive inputs only; their update paths
on real rows need a manual check. Note: source-side test transactions still advance Oracle identity values
(sequences are not transactional).

## Carry-forward for the application team
1. `NUMBER(1)` flags are `smallint` 0/1 — Boolean mappings need `@JdbcTypeCode(SqlTypes.SMALLINT)`.
2. `DATE` columns are `timestamp(0)` — `LocalDate` mappings need `@JdbcTypeCode(SqlTypes.TIMESTAMP)`.
3. `BLOB` → `bytea` — drop `@Lob`, use `@JdbcTypeCode(SqlTypes.VARBINARY)`.
4. `fulltext_redesign`: rewrite `CONTAINS/SCORE` to the `to_tsvector('english', coalesce(search_text,''))` expression.
5. Packages flattened to `<package>_<subprogram>`; business errors are SQLSTATE `U0001` / `U0002`.
6. Untested on real data (LOW_COVERAGE): the order/cart paths.
