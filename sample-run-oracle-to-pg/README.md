# Sample run — Oracle `DEMO` → Aurora PostgreSQL (+ Java app)

A complete, real run of dbmig-aidlc, **converted from scratch** (no DMS SC), captured end to end and
**masked** (hosts, account ids, local paths and credentials replaced with placeholders). It includes the
optional application-modernization module for the Spring Boot / JPA app `JavaBobsUsedBooks`.

- **Source:** Oracle 19c EE, schema `DEMO`  ·  **Target:** Aurora PostgreSQL **18.6**, schema `demo`
- **Refreshed 2026-10-30** on a fresh 18.6 cluster with the refreshed playbooks and the context wiring (target baseline, quick tips, target-aware construct hints, citation count). The previous run targeted 17.7.
- **App:** Spring Boot 4.0.6, Java 21, Hibernate 7 / Spring Data JPA, Thymeleaf, raw JDBC demo classes

## Result at a glance

| Phase | Result |
|---|---|
| Inventory | 14 user tables, 30 indexes, 12 identity sequences, 5 functions, 5 procedures, 5 packages, 1 trigger; 4 `DR$` Oracle Text tables + 3 indexes **excluded automatically**; decision item `fulltext_redesign` raised |
| Tables | **14/14** applied first pass (FK guard: no invented FKs — `ORDERS` has none in the source) |
| Stored code | **15/15** first pass (5 packages converted spec+body as one unit, flattened to `<pkg>_<subprogram>`) |
| Data | 199 rows; **14/14** tables reconcile; post-data FKs + trigger **7/7** |
| Equivalence tests | **58/58** first run (write paths proven with real deltas; target behaviour differences from the PG 18 baseline covered; 4 `LOW_COVERAGE` objects reported separately) |
| Identity | `reset-identity`: **12/12** identity columns safe (runbook step generated from the catalog) |
| App | 18 files changed; builds; **boots with `ddl-auto=validate` first time**; full-text search verified via index scan; `LoadCoverImages` utility verified against the target |
| Traceability | `conversion-log.md` cites **9 distinct playbook topics** (`./dbmig status` counts them) |
| Shared context | `_context-schema.md` / `_context-code.md` ≈ 40 KB each, read once per session (datatype map, engine checks, PG 18 baseline sections, quick tips, topic index) |

## Folder map

| Folder | What's in it |
|---|---|
| `00-intake/` | intake summary |
| `01-assessment/` | `inventory-DEMO.yaml/.json` (incl. `excluded_internal_objects`, `decision_items`), `migration-plan.md` |
| `02-construction/` | `_context-schema.md`, `_context-code.md` (shared context, read once), `prompts/` + `code_prompts/` (batched bundles with detected-construct hints), `ddl/demo/`, `code/demo/`, manifests (with `source_fk_count`), apply reports, `conversion-log.md` |
| `03-validation/` | `_context-tests.md`, `test_prompts/` (include the converted target code), `tests/` (specs; package specs mix function/procedure cases via per-case `type`), `equivalence-report-DEMO.md`, `reconcile_report`, `validation-summary.md` |
| `04-operations/` | cutover runbook, rollback plan, monitoring (AI-generated disclaimer), `identity-reset-DEMO.md` (generated runbook step) |
| `05-application/` | app intake, `app-scan.md` (deterministic pre-scan), change plan, conversion log + `app.diff` (exact changes), build/boot report, app cutover, `backup/<ts>/MANIFEST.md` (a real run keeps mirrored originals there; omitted in this sample) |
| `data/` | per-table load state + load report |

## Notable decisions

- `NUMBER(1)` flags → `smallint` 0/1 (not boolean); `DATE` → `timestamp(0)`; `BLOB` → `bytea`;
  `NUMBER(10)` → `bigint`. Each creates a predictable JPA obligation — listed by `app-scan` C1 and fixed
  with `@JdbcTypeCode(SqlTypes.SMALLINT | TIMESTAMP | VARBINARY)`.
- Oracle Text `CONTEXT` → `GIN (to_tsvector('english', coalesce(search_text,'')))`; the app's
  `CONTAINS/SCORE` query uses the same expression (`EXPLAIN` → Bitmap Index Scan on `books_text_idx`).
- `reporting_pkg_get_top_books` (PIPELINED) → `RETURNS TABLE` with column types taken from the converted
  columns — the declared-type hazard that failed at execution in an earlier run.
- `COMMIT` removed from 4 procedures (caller owns the transaction); their tests use non-existent keys.

## Found during this run (and fixed in the framework)

- **Baseline version check:** the PG 18 baseline would have been injected unchanged into a 17.x run (18-only
  `VIRTUAL` columns, `uuidv7()`, `NOT ENFORCED`). `engine.yaml` now declares `target_baseline.verified_for`, and the
  context carries a caution when `target.version` does not match.
- **App utility:** `utils/LoadCoverImages` reads `application.properties` without Spring, so the externalised
  `${DB_*}` settings reached `DriverManager` verbatim. Missed by the previous run; fixed with placeholder resolution.
- **Test harness:** `compare: resultset` was documented but compared only the first value; now every row and column
  is compared.
- Operations documents now start with the verbatim disclaimer the operations skill requires (the previous sample
  used a shortened one).

## Reproducing

```bash
./dbmig test-connection --side both
./dbmig inventory      --schema DEMO --project demo
./dbmig convert-schema --schema DEMO --project demo   # the assistant converts each bundle
./dbmig apply-schema   --schema DEMO --project demo
./dbmig convert-code   --schema DEMO --project demo
./dbmig apply-schema   --schema DEMO --project demo --code
./dbmig migrate-data   --schema DEMO --project demo --workers 4
./dbmig apply-schema   --schema DEMO --project demo --post-data
./dbmig compare        --schema DEMO --project demo
./dbmig gen-tests      --schema DEMO --project demo   # after convert-code: bundles carry target code
./dbmig run-tests      --schema DEMO --project demo
./dbmig reset-identity --schema DEMO --project demo   # dry run; --apply at cutover
./dbmig app-scan       --app-dir <app-dir>/JavaBobsUsedBooks --project demo --target-schema demo
```

> AI-generated artifacts — review everything before relying on it. See [DISCLAIMER.txt](../DISCLAIMER.txt).
