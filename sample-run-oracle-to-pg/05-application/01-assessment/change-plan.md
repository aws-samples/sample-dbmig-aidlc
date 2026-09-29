# Change plan — JavaBobsUsedBooks → PostgreSQL (like-for-like)

Built from `dbmig app-scan` (`app-scan.md`: 119 files scanned, **19 flagged**, 13 JPA entities, 128
mapped fields checked against the live `demo` schema) plus the DB carry-forward list.

| # | Site | Class | Change |
|---|---|---|---|
| 1 | `application.properties` | mechanical | PG URL (`currentSchema=demo&sslmode=require`), `org.postgresql.Driver`, remove OracleDialect; **plaintext password → `${DB_PASSWORD}`** (user/host/db also env) |
| 2 | `pom.xml` | mechanical | remove `ojdbc17` (PG driver already present) |
| 3 | 10 × `Boolean` on `smallint` (Address, Customer ×4, Listing ×3, PasswordResetToken, ShoppingCartItem) | required | drop `columnDefinition="NUMBER(1)"`, add `@JdbcTypeCode(SqlTypes.SMALLINT)` |
| 4 | 5 × `LocalDate` on `timestamp(0)` (Book.publishDate, Customer.dateOfBirth, Order.shipped/delivered/cancelledDate) | required | `@JdbcTypeCode(SqlTypes.TIMESTAMP)` (keep LocalDate — smallest change) |
| 5 | `BookCover.coverImage` `@Lob byte[]` on `bytea` | required | drop `@Lob`, add `@JdbcTypeCode(SqlTypes.VARBINARY)` |
| 6 | `BookRepository.fullTextSearchBooks` (`CONTAINS/SCORE`, 3-line literal) | BEHAVIOURAL | tsvector @@ tsquery + `ts_rank`, expression identical to `books_text_idx` |
| 7 | `BookService.prepareSearchQuery` builds `fuzzy(t, 40) OR …` (Oracle Text query language — flagged as a Tier-3 fragment) | BEHAVIOURAL | plain terms OR-ed for `websearch_to_tsquery`; fuzzy edit-distance matching is lost (pg_trgm = redesign option) |
| 8 | `DatabaseInfoConfig/Controller` split URL on Oracle `@//`, fallback echoed the raw URL | mechanical + security | parse after `//`, drop the query string, no raw-URL fallback |
| 9 | `demo/OracleBookRepository`, `demo/OracleBookService` | **pre-existing broken** | columns/tables absent from the SOURCE (`b.name`, `SALES`, `order_date` …, verified in ALL_TAB_COLUMNS/ALL_TABLES): dialect-only conversion (ROWNUM→LIMIT *behavioural*, NVL, DECODE, TO_DATE, ADD_MONTHS, LISTAGG, MONTHS_BETWEEN) + loud flag |
| 10 | `CustomerRepository` `{ call get_customer_history }` | **pre-existing broken** | routine absent in the source (ALL_OBJECTS: 0 rows) — unchanged, flagged |
| — | 5 × `Integer` on `bigint` (Book.year, Listing.quantity/status, OrderItem.quantity, ShoppingCartItem.quantity) | advisory | no change: Hibernate validate accepts it; the source NUMBER(10) already exceeded int32 |
| — | `/search` default `sort=name` → JPQL `b.name` does not exist on `Book` | pre-existing (JPQL) | not migration-caused; noted for the app owner |
