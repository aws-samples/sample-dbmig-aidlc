# Build Report — JavaBobsUsedBooks (Validation)

## Build
- `mvn -q -B clean compile` → **exit 0, 0 errors** (baseline before conversion also passed, so
  the conversion introduced no compile regressions).
- `mvn -q -B test` → exit 0. **No `src/test` directory exists** — a green test run proves
  nothing here; recorded as a gap, not as evidence.

## Live-target verification (read-only PREPARE against demodb.demo)
| Statement | Result |
|---|---|
| Full-text main query (site 1) | **PREPARE OK** — and `EXPLAIN` confirms `books_text_idx` (GIN) is used; sample term `iron` returns 1 hit, matching the DB-phase parity tests |
| Full-text countQuery | **PREPARE OK** |
| Demo-class queries (sites 2, B3–B5) | PREPARE FAIL — `b.name`, `is_featured`, `quantity`, `created_date` do not exist in the migrated `books` table |

The demo-class failures are the **pre-existing phantom schema** documented at Inception: those
classes reference columns and a `sales` table that never existed in the Oracle `DEMO` schema
either. They were equally broken before conversion; the dialect conversion is still correct and
the failure mode is unchanged. Decision on deleting/repairing the demo package is with the app
owner.

## Verification matrix
| Site | Status |
|---|---|
| 1 (full-text, both queries) | compiled + **prepared against target** + index-use verified |
| 4 (datasource config) | compiled; will be exercised at app startup |
| 5 (pom) | compiled (dependency resolution passed) |
| 2, B3–B8 (demo classes) | compiled; **UNVERIFIED at runtime** — phantom schema, pre-existing |
| URL-parser fixes (2 files) | compiled; logic verified by inspection against both URL formats |
| 12 (get_customer_history) | not converted — **BLOCKED**, needs decision |

## Remaining behavioural risks (owners needed)
1. Search semantics: `plainto_tsquery` ANDs terms; Oracle Text default differed. Ranking is
   `ts_rank`, not `SCORE`. UI relevance ordering may shift. Owner: app team.
2. `LIMIT`-after-sort vs `ROWNUM`-before-sort in `findBooksByGenre` (intent-preserving, results
   may differ vs Oracle). Owner: app team.
3. `customer_age_months` epoch approximation vs Oracle calendar months (demo code). Owner: app team.

## Residual work
- Decide the fate of `get_customer_history` (blocked item).
- Decide the fate of the `demo/` package (phantom schema).
- Add a test suite — currently none exists; the converted search path deserves one.
- Delete the 5 stale `.bak` files (separate cleanup).
- Set `DB_PASSWORD` in the runtime environment (plaintext credential removed from properties).
