# Supplementary Verification — checks outside the delta harness

The `run-tests` harness compares function return values and procedure **net effects**. Three
classes of behaviour cannot be proven that way, so they were verified directly against both
engines and recorded here.

## 1. OUT parameters of read-only procedures
Three procedures return everything through OUT parameters and write nothing, so net-effect
probes would be identically zero on both engines and would prove nothing. Each was invoked on
both engines and **every** OUT value compared (Oracle `callproc` with bind vars vs PostgreSQL
`CALL`, which returns OUT values as a row in PG 14+).

| Procedure | OUT parameters compared | Result |
|---|---|---|
| `GENERATE_SALES_REPORT` | `p_total_orders`, `p_total_revenue`, `p_avg_order_value` | **all MATCH** (0, 0, 0) |
| `REPORTING_PKG.GET_CUSTOMER_STATS` | `p_total_orders`, `p_total_spent`, `p_avg_order`, `p_last_order_date` — for real customers 1, 2, 3 | **all MATCH** (0, 0, 0, NULL) |
| `BOOK_PKG.GET_BOOK_DETAILS` | `p_title`, `p_author`, `p_total_qty`, `p_avg_price` — for real books 1, 2, 56 | **all MATCH** (e.g. `2020: The Apocalypse` / `Li Juan` / 0 / 0) |

`p_last_order_date` returning NULL on both sides confirms `MAX(TRUNC(created_on))` →
`max(created_on::date)` agrees over an empty set. The 0 values confirm `NVL(...,0)` →
`coalesce(...,0)` for both `SUM` and `AVG` over empty sets.

## 2. Error parity (raise branches)
An exception aborts a harness case, so the raise paths were driven directly. **A real defect
was found and fixed here.**

| Scenario | Oracle | PostgreSQL (after fix) | Verdict |
|---|---|---|---|
| Invalid action (`ORA-20002`) | `ORA-20002: Invalid action. Use APPROVE or REJECT` | `[U0002] Invalid action. Use APPROVE or REJECT` | same logical error, same message |
| Insufficient inventory (`ORA-20001`) | `ORA-20001: Insufficient inventory` | `[U0001] Insufficient inventory` | same logical error, same message |
| Missing row (`NO_DATA_FOUND`) | `ORA-01403: no data found` | `[P0002] query returned no rows` | `SELECT INTO STRICT` correctly raises instead of returning NULL |

### Defect found: SQLSTATE collision (fixed)
The first conversion mapped `RAISE_APPLICATION_ERROR(-20001/-20002)` to `P0001`/`P0002`.
**`P0002` is PostgreSQL's built-in `no_data_found`**, and the `P0` class is reserved for
PL/pgSQL (`P0001` raise_exception, `P0002` no_data_found, `P0003` too_many_rows). An
application handler for "invalid action" would therefore also have swallowed genuine
NO_DATA_FOUND errors — the two were provably indistinguishable in testing (both reported
`P0002`). Remapped to the unassigned `U0` class: **`ORA-20001` → `U0001`, `ORA-20002` → `U0002`**,
a collision-free, self-documenting 1:1 mapping of the Oracle error number. Re-applied and
re-verified: the three scenarios now return three distinct SQLSTATEs.

## 3. Full-text search (the Oracle Text → GIN redesign)
`CONTAINS()` has no PostgreSQL equivalent, so search parity was measured directly by running
the same terms through Oracle Text and the new GIN index.

| Term | Oracle `CONTAINS` | PostgreSQL `@@ to_tsquery` |
|---|---|---|
| apocalypse | 1 | 1 |
| iron | 1 | 1 |
| gold | 1 | 1 |
| dark | 2 | 2 |
| children | 1 | 1 |
| wolf | 1 | 1 |
| juan | 1 | 1 |
| richard | 1 | 1 |

All 8 real-data terms match. Additional checks:
- **Index is actually used:** `EXPLAIN` shows `Bitmap Index Scan on books_text_idx`, not a
  sequential scan — the GIN index is live, not decorative.
- **Trigger parity:** `search_text` is identical for all 56 rows between engines (0 mismatches),
  and a fresh `INSERT` on the target derives
  `trigger probe ada lovelace 12345x` — i.e. the PL/pgSQL trigger reproduces Oracle's
  `LOWER(...) || ' ' || LOWER(NVL(...))` logic including the NULL→`''` behaviour.
- Note: stopwords behave as expected — `to_tsquery('english','the')` returns 0 because
  `the` is an English stopword. Applications must not rely on stopword matching.

## 4. Harness credibility (negative control)
Because 103/103 passing invites the question "do these tests actually test anything?", a
deliberate negative control was run once and then removed:

| Case | Oracle | PostgreSQL | Outcome |
|---|---|---|---|
| `SELECT 1` vs `SELECT 2` | 1 | 2 | **FAIL, as intended** — the harness does compare and can fail |
| `REGEXP_REPLACE` without the `g` flag | 13 | 15 | **FAIL, as intended** — proves the `g`-flag trap is real |

The second control is the important one: it demonstrates that had the `'g'` flag been omitted,
`validation_pkg_is_valid_isbn` would have returned the wrong answer — and the passing `i3`/`i4`
cases prove the shipped code gets it right. Both control entries are recorded as `resolved` in
`follow-up.yaml` with this explanation.

## 5. Source-database integrity
Four procedures **commit in their Oracle source**, so rollback cannot undo source-side changes
(`gen-tests` flagged them `test_mode: manual`). Every case for them targets a non-existent key,
so zero rows are affected and the `COMMIT` commits nothing. Verified afterwards:

- Source total: **199 rows**; target total: **199 rows** — unchanged, no per-table drift.
- `LISTINGS` quantity sum: source **396**, target **396** — the `reduce_inventory` write tests
  left no residue on either side.
