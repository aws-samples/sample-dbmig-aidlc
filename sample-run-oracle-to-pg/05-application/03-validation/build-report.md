# Build & validation report — JavaBobsUsedBooks → Aurora PostgreSQL 18.6

| Check | Result |
|---|---|
| Compile `mvn -q -B clean compile` (Java 21) | **pass**, first attempt |
| Boot `mvn spring-boot:run` with `ddl-auto=validate` against `demodb.demo` | **pass, first boot** (`Started BobsUsedBooksApplication in 10.3 s`); all 16 planned type fixes held, no boot-time fixes needed |
| Errors in the application log during the smoke run | 0 (no `PSQLException`, no Hibernate errors) |
| `LoadCoverImages` utility against the target | **pass** — 56 covers loaded with the `${DB_*}` settings resolved from the environment |

## Verification matrix

| Site | How verified | Result |
|---|---|---|
| Home `/demoapp/` | HTTP GET | 200 |
| Book list `/demoapp/books` | HTTP GET | 200 |
| Book detail `/demoapp/books/1` | HTTP GET | 200 |
| Cover image `/demoapp/books/1/cover` (`bytea` via `VARBINARY`) | HTTP GET | 200, `image/png`, 111,650 bytes |
| Full-text `/demoapp/fulltextsearch?query=gothic` | HTTP GET | 200, results contain "Gothic" |
| Full-text multi-term `?query=nightingale moscow` (`or` join) | HTTP GET | 200, results returned |
| Full-text plan | `EXPLAIN` of the exact app query | **Bitmap Index Scan on `books_text_idx`** |
| Keyword search `/demoapp/search?keyword=dark` | HTTP GET | 200 |
| DB-info banner (URL parsing) | page HTML | `postgres@<cluster-endpoint>:5432/demodb` (no query string) |

**UNVERIFIED:** write paths (checkout, cart, offers, admin approval) — read-only smoke; the order/cart tables are
empty in the source (LOW_COVERAGE in the DB run). Fuzzy (misspelling) search is intentionally not reproduced.
**Pre-existing broken (unchanged behaviour):** `demo/*` classes and `CustomerRepository.getCustomerPurchaseHistory`
fail on Oracle and on PostgreSQL alike.
