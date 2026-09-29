# Build & validation report — JavaBobsUsedBooks on Aurora PostgreSQL

1. **Build:** `mvn -q -B clean compile` → exit 0 (one intermediate failure: missing `JdbcTypeCode` imports — fixed).
2. **Boot (required):** `mvn spring-boot:run` with `SPRING_JPA_HIBERNATE_DDL_AUTO=validate`, credentials
   from env → `Started BobsUsedBooksApplication in 9.3 seconds`. **Zero boot-time mapping failures** —
   all 16 required type fixes were planned from `app-scan`'s C1 table (the previous workshop found three
   of these only at boot, one failure per table).
3. **Endpoints (read-only):** `/` 200 · `/books` 200 · `/api/books/43/cover` 200 (bytea image) ·
   `/search?query=circus&sort=title` 200 (Night Circus) · `/fulltextsearch?query=gothic` 200 (Mexican Gothic) ·
   `/fulltextsearch?query=magic circus` 200 (2 hits) · `/fulltextsearch?query=circus & (` 200 (no syntax error).
4. **Full-text plan:** `EXPLAIN … @@ …` → `Bitmap Index Scan on books_text_idx` (query and index expressions match).
5. **Found during validation (fixed):** first full-text run returned 0 hits — `BookService` wrapped terms
   in Oracle Text `fuzzy(t, 40)` syntax. Not SQL, so the first scan missed it; `app-scan` now flags
   full-text query-language fragments (Tier 3).

## Verification matrix
| Site | Status |
|---|---|
| config / driver / dialect | booted |
| 16 entity type fixes | booted (validate) |
| full-text query + builder | booted + endpoint + EXPLAIN |
| URL parsing | compiled |
| demo/Oracle* classes, get_customer_history | **UNVERIFIED** — pre-existing broken, not reachable |

## Remaining behavioural risks (owner: app team)
ROWNUM→LIMIT intent in demo class; fuzzy matching lost in search; `ts_rank` ordering ≠ Oracle `SCORE`.
