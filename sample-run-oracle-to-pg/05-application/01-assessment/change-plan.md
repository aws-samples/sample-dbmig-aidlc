# Change plan — JavaBobsUsedBooks → Aurora PostgreSQL 18.6 (like-for-like)

Built from `app-scan.md` (119 files, 20 flagged, 128 mapped fields checked against the live `demo` schema),
`app-contract.md` and the DB carry-forward list. **Nothing has been edited yet.** Backup: full tree to
`05-application/backup/<YYYYMMDD-HHMMSS>/` before the first edit (not a git repo).

## Behavioural changes (review first)

### 1. `repositories/BookRepository.java:96-101`   [BEHAVIOURAL]
Current:  `WHERE CONTAINS(search_text, ?1, 1) > 0 ORDER BY SCORE(1) DESC` (+ count query)
Proposed: `WHERE to_tsvector('english', coalesce(b.search_text, '')) @@ websearch_to_tsquery('english', ?1)
          ORDER BY ts_rank(to_tsvector('english', coalesce(b.search_text, '')), websearch_to_tsquery('english', ?1)) DESC`
Why:      `fulltext_redesign` decision A; expression identical to `books_text_idx` (engine check "Oracle Text").
Risk:     ranking differs from Oracle `SCORE`; a different expression would silently seq-scan.

### 2. `services/BookService.java:174-183`   [BEHAVIOURAL]
Current:  builds `fuzzy(term, 40) OR …` (Oracle Text query language)
Proposed: plain terms joined with ` or ` for `websearch_to_tsquery`
Why:      PostgreSQL treats `fuzzy(...)` as literal words → no matches.
Risk:     edit-distance (misspelling) matching is lost; `pg_trgm` similarity is the redesign option.

### 3. `demo/OracleBookRepository.java:36-39`   [BEHAVIOURAL, pre-existing broken class]
Current:  `AND ROWNUM <= 100 ORDER BY b.name`
Proposed: `ORDER BY b.name LIMIT 100`
Why:      ROWNUM filters before the sort; LIMIT after it — converted to the evident intent.

## Mechanical / required changes

| # | Site | Change | Why |
|---|---|---|---|
| 4 | `application.properties` | PG URL `jdbc:postgresql://${DB_HOST}:${DB_PORT:5432}/${DB_NAME}?currentSchema=demo&sslmode=require`; `org.postgresql.Driver`; remove `OracleDialect`; **plaintext password → `${DB_PASSWORD}`**, username `${DB_USERNAME}` | app-config.yaml; secrets out of the repo |
| 5 | `pom.xml` | remove `ojdbc17` (PG driver already present) | app-config.yaml |
| 6 | 10 × `Boolean` (Address, Customer ×4, Listing ×3, PasswordResetToken, ShoppingCartItem) | drop `columnDefinition="NUMBER(1)"`, add `@JdbcTypeCode(SqlTypes.SMALLINT)` | carry-forward 1 |
| 7 | 5 × `LocalDate` (Book.publishDate, Customer.dateOfBirth, Order.shipped/delivered/cancelledDate) | `@JdbcTypeCode(SqlTypes.TIMESTAMP)` | carry-forward 2 |
| 8 | `BookCover.coverImage` | drop `@Lob`, add `@JdbcTypeCode(SqlTypes.VARBINARY)` | carry-forward 3 |
| 9 | `DatabaseInfoConfig`, `DatabaseInfoController` | parse after `//`, drop the query string, no raw-URL fallback | URL format + credential-leak path |
| 10 | `utils/LoadCoverImages.java:24-26` | resolve `${VAR}` / `${VAR:default}` from the environment before `DriverManager.getConnection` | **new**: change 4 would otherwise pass literal placeholders to the driver |
| 11 | `demo/OracleBookRepository`, `demo/OracleBookService` | dialect-only conversion (NVL, DECODE, TO_DATE, ADD_MONTHS, LISTAGG, MONTHS_BETWEEN) + PRE-EXISTING BROKEN banner | pre-existing broken (source catalog evidence in inventory.md) |
| 12 | `CustomerRepository` `get_customer_history` | comment only — routine absent in the source | pre-existing broken |

No change: 5 × `Integer` on `bigint` (advisory), `rs.getInt` on `COUNT(*)`, `SQLException` message logging.

## Verification plan
`mvn -q -B clean compile`; boot with `ddl-auto=validate` against `demodb.demo`; smoke `/demoapp/`, `/demoapp/books`,
`/demoapp/fulltextsearch?query=gothic` (+ `EXPLAIN` showing a Bitmap Index Scan on `books_text_idx`), a cover image,
the DB-info banner; run `LoadCoverImages` against the target.
