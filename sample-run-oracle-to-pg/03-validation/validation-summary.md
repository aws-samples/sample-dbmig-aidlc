# Validation Summary — DEMO (Oracle 19c → Aurora PostgreSQL 17.7)

**Result: PASS.** Full data load reconciled exactly, 103/103 equivalence cases passed, and
**0 open follow-up items**. One real defect was found during validation and fixed (SQLSTATE
collision — see below).

## 1. Data load (strategy `full`, data_volume `full`)
`migrate-data` copied **199 rows across all 14 tables** in FK-dependency order (4 tiers,
8 workers), then advanced the identity sequences.

## 2. Reconciliation — stronger than row counts
| Check | Scope | Result |
|---|---|---|
| Row counts (`dbmig compare`) | 14/14 tables | **all match** |
| **Cell-level value comparison** | 199 rows × all columns = **2,229 cell values** across the 9 populated tables | **byte-for-byte identical** |
| BLOB fidelity | 56 `BOOKS_COVER.COVER_IMAGE` images compared by SHA-256 | **all identical** |
| Identity advance | 12 IDENTITY tables | **all advanced past `MAX(id)`** — next insert cannot collide |
| Deferred post-data objects | 16 foreign keys + 1 trigger | **applied after the load, 7/7 units** |

Row counts alone would not have caught a datatype or timestamp-truncation error, so values
were compared column-by-column with normalization (numeric scale, timestamps, BLOB hashes).
This is what proves `DATE → timestamp(0)` lost no time-of-day and `NUMBER(38,2) → numeric(38,2)`
lost no precision.

## 3. Equivalence tests — 103/103 passed
16 units, generated from **real sampled data only**, each case executed on **both** engines
inside a transaction that is rolled back.

| Unit | Type | Cases | Result |
|---|---|---|---|
| CALCULATE_DISCOUNT_PCT | function | 7 | pass |
| GET_CONDITION_NAME | function | 6 | pass |
| GET_CUSTOMER_FULL_NAME | function | 6 | pass |
| GET_CUSTOMER_LIFETIME_VALUE | function | 5 | pass |
| GET_GENRE_NAME | function | 6 | pass |
| BOOK_PKG | function | 13 | pass |
| VALIDATION_PKG | function | 19 | pass |
| INVENTORY_PKG_FUNCTIONS | function | 11 | pass |
| GENERATE_SALES_REPORT | function (OUT via wrapper) | 5 | pass |
| INVENTORY_PKG | procedure (net effect) | 4 | pass |
| ORDER_PKG | procedure (net effect) | 6 | pass |
| REPORTING_PKG | procedure (net effect) | 4 | pass |
| ARCHIVE_OLD_ORDERS | procedure (net effect) | 3 | pass |
| CLEAR_SHOPPING_CART | procedure (net effect) | 2 | pass |
| PROCESS_CUSTOMER_OFFER | procedure (net effect) | 3 | pass |
| SET_BOOK_FEATURED | procedure (net effect) | 3 | pass |
| **Total** | | **103** | **103 pass / 0 fail** |

### What the risky conversions were actually tested against
- **`REGEXP_REPLACE` `'g'` flag** — cases `i3`/`i4` feed multi-separator ISBNs; the negative
  control proved that without `'g'` PostgreSQL returns 15 instead of Oracle's 13, flipping the
  validity result. The shipped code is correct.
- **NULL string concatenation** — case `c6` asserts Oracle's `NULL || ' ' || 'Doe'` = `' Doe'` is
  reproduced by the `coalesce` rewrite (a bare PG concat would have returned NULL).
- **`SELECT INTO STRICT`** — missing-id and NULL-id cases confirm `NO_DATA_FOUND` still fires and
  `'Unknown'` / `'Unknown Customer'` is returned, rather than a silent NULL.
- **PIPELINED → `RETURNS TABLE`** — REPORTING_PKG cases **seed real orders inside the rolled-back
  transaction**, so `get_top_books` is exercised against non-empty data: row counts, `total_sold`,
  `revenue`, the `ORDER BY total_sold DESC` ranking, the `FETCH FIRST` → `LIMIT` conversion, and
  exclusion of `CANCELLED` orders all match.
- **Empty-set aggregates** — `NVL/coalesce(SUM|AVG|COUNT, 0)` returns 0 (never NULL) on both
  engines. Relevant because `ORDERS`/`ORDER_ITEMS` are empty and `LISTINGS` has no `'STORE'` rows.
- **Identity inserts** — ORDER_PKG cases insert into `ORDERS`/`ORDER_ITEMS`, proving the identity
  columns allocate cleanly on the target after the post-load advance.
- **Preserved source quirk** — `update_order_status` writes NULL over the non-matching date
  columns (the source `CASE` has no `ELSE`); cases `o5`/`o6` assert that quirk was kept, not "fixed".

Full methodology: `engines/oracle-to-postgresql/checks/equivalence-spec.md`.
Machine-readable results: `equivalence-report-DEMO.yaml` / `.md`.

## 4. Verified outside the delta harness
See **`supplementary-verification.md`** for detail. Summary:
- **All OUT parameters** of the 3 read-only OUT-param procedures compared value-by-value — all match.
- **Error parity** — `ORA-20001`/`ORA-20002` and `NO_DATA_FOUND` all raise the correct, distinct errors.
- **Full-text search** — all 8 real-data terms return counts identical to Oracle `CONTAINS`, and
  `EXPLAIN` confirms the GIN index is used (Bitmap Index Scan). Trigger-derived `search_text` is
  identical for all 56 rows.
- **Negative control** — the harness was proven able to FAIL, so 103/103 is meaningful.
- **Source integrity** — source still 199 rows, `LISTINGS` quantity sum 396 on both sides.

## 5. Defect found and fixed during validation
**SQLSTATE collision.** `ORA-20002` had been mapped to `P0002`, which **is PostgreSQL's built-in
`no_data_found`** (the `P0` class is reserved for PL/pgSQL). An application handler for "invalid
action" would also have caught genuine NO_DATA_FOUND errors. Remapped to the unassigned `U0`
class — `ORA-20001` → `U0001`, `ORA-20002` → `U0002` — then re-applied, re-verified (three
distinct SQLSTATEs), and the full suite re-run with no regressions.

## 6. Open follow-up items
**None.** `follow-up.yaml` holds only the two intentional negative-control entries, both marked
`resolved` with an explanation.

## 7. Carry-forward for the application team (not defects)
1. **Search predicates must be rewritten** in application code:
   `CONTAINS(search_text, :q) > 0` → `to_tsvector('english', coalesce(search_text,'')) @@ to_tsquery('english', :q)`.
   English stopwords (e.g. `the`) will not match — Oracle Text behaved likewise for the default lexer.
2. **Error codes changed**: catch `U0001`/`U0002` instead of `ORA-20001`/`ORA-20002`.
3. **Procedures no longer `COMMIT`** (4 of them) — the caller now owns the transaction, which is
   the PostgreSQL idiom. Application code must commit explicitly.
4. **Packages are flattened**: call `demo.order_pkg_create_order(...)`, not `ORDER_PKG.CREATE_ORDER(...)`.
5. `PERSISTENT_LOGINS` was an IOT and is now a heap table with a PK — physical clustering is not
   preserved (consider `CLUSTER` only if access patterns require it).
