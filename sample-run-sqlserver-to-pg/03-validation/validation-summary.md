# Validation summary — dbo → dbo (Aurora PostgreSQL 18.6)

| Check | Result |
|---|---|
| Data load | 2,963 rows, 20 tables |
| Post-data (FKs + triggers) | 6/6 |
| Reconcile | **20/20** match |
| Equivalence tests | **69/69** on the first run (68 carried cases + r4, a full result-set comparison of `uspgetbillofmaterials(609, '2011-01-01')`: 3 rows × 8 columns, recursion depth 2) |
| Identity | 14/14 safe |

**Finding:** the three original `uspgetbillofmaterials` cases (products 800/750/977) return **0 rows on both
engines** — those products are not assemblies in this data, so they only proved the empty path. r4 now covers
the populated path, using the new `compare: resultset` support in `run-tests`.

**LOW_COVERAGE:** `usplogerror` (ErrorLog empty); `uspgettopregion` is date-relative (the 6-month window is empty
on both engines). **Manual review:** `vwopencoupons` (`CURRENT_USER` semantics); raised-error paths are not compared.

## Carry-forward for the application team
1. Result-set procedures are functions: `SELECT * FROM dbo.<fn>(…)` instead of `EXEC`.
2. `bit` → `boolean`; EF `int` properties on `bit` columns need `HasConversion<bool>`.
3. `citext` lives in schema `dbo`: the app must connect with `SearchPath=dbo`.
4. Identifiers are lower-case: EF Core must fold table/column names in `OnModelCreating`.
5. `"order"` is a reserved word (quoted table).
