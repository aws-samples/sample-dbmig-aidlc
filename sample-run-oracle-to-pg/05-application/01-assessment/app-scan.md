# App scan — `JavaBobsUsedBooks` (oracle-to-postgresql)

Deterministic pre-scan by `dbmig app-scan` (read-only). **Open only the flagged files**; full detail in `app-scan.yaml`.

- files in scope: **119** (.java 106, .sql 6, .js 5, .xml 1, .properties 1)
- frameworks detected: JPA/Hibernate (14 file(s)), Raw JDBC (1 file(s))
- excluded dirs: vendored-asset×145
- leftovers (not conversion targets): src/main/java/com/bobsusedbooks/controllers/ReferenceDataController.java.bak, src/main/resources/application.properties.bak, src/main/resources/db/oracle/01_user.sql.bak, src/main/resources/templates/admin/reference-data/index.html.bak
- **flagged files: 20 of 119**

| Category | Sites | Files |
|---|---|---|
| A. config (datasource/driver/dialect; plaintext secrets) | 8 | 2 |
| A. connection strings/URLs built in code | 2 | 2 |
| B. embedded SQL with source-dialect constructs | 10 | 4 |
| B. other embedded SQL (no construct hit — still review for case/quoting) | 25 | 6 |
| C1. mapped fields with a REQUIRED type fix | 16 | 8 |
| C1. type advisories (not blockers; review) | 5 | 4 |
| C1. mapping issues (missing table/column, identifier case) | 0 | 0 |
| D. stored-routine call sites | 1 | 1 |
| E. error-code handling | 1 | 1 |
| F. result-set typing / column-name access | 8 | 2 |
| H. source-engine SQL scripts shipped with the app (flag; not converted unless in scope) | 5 | 5 |

Entities/models: 13 (JPA/Hibernate 13); 128 mapped field(s) checked against **live target catalog (schema demo)**.

## C1. Required type fixes (entity field ↔ migrated column)

- `src/main/java/com/bobsusedbooks/entities/Address.java:26` JPA/Hibernate Address.isDefault (Boolean) → addresses.is_default [smallint]: Boolean on smallint column: @JdbcTypeCode(SqlTypes.SMALLINT) (remove columnDefinition)
- `src/main/java/com/bobsusedbooks/entities/Book.java:31` JPA/Hibernate Book.publishDate (LocalDate) → books.publish_date [timestamp without time zone]: date-only type on timestamp without time zone column: keep LocalDate + @JdbcTypeCode(SqlTypes.TIMESTAMP)
- `src/main/java/com/bobsusedbooks/entities/BookCover.java:26` JPA/Hibernate BookCover.coverImage (byte[]) → books_cover.cover_image [bytea]: @Lob on bytea (validates as oid): drop @Lob, add @JdbcTypeCode(SqlTypes.VARBINARY)
- `src/main/java/com/bobsusedbooks/entities/Customer.java:30` JPA/Hibernate Customer.dateOfBirth (LocalDate) → customers.date_of_birth [timestamp without time zone]: date-only type on timestamp without time zone column: keep LocalDate + @JdbcTypeCode(SqlTypes.TIMESTAMP)
- `src/main/java/com/bobsusedbooks/entities/Customer.java:33` JPA/Hibernate Customer.emailVerified (Boolean) → customers.email_verified [smallint]: Boolean on smallint column: @JdbcTypeCode(SqlTypes.SMALLINT) (remove columnDefinition)
- `src/main/java/com/bobsusedbooks/entities/Customer.java:38` JPA/Hibernate Customer.accountExpired (Boolean) → customers.account_expired [smallint]: Boolean on smallint column: @JdbcTypeCode(SqlTypes.SMALLINT) (remove columnDefinition)
- `src/main/java/com/bobsusedbooks/entities/Customer.java:41` JPA/Hibernate Customer.credentialsExpired (Boolean) → customers.credentials_expired [smallint]: Boolean on smallint column: @JdbcTypeCode(SqlTypes.SMALLINT) (remove columnDefinition)
- `src/main/java/com/bobsusedbooks/entities/Customer.java:44` JPA/Hibernate Customer.accountLocked (Boolean) → customers.account_locked [smallint]: Boolean on smallint column: @JdbcTypeCode(SqlTypes.SMALLINT) (remove columnDefinition)
- `src/main/java/com/bobsusedbooks/entities/Listing.java:64` JPA/Hibernate Listing.isFeatured (Boolean) → listings.is_featured [smallint]: Boolean on smallint column: @JdbcTypeCode(SqlTypes.SMALLINT) (remove columnDefinition)
- `src/main/java/com/bobsusedbooks/entities/Listing.java:67` JPA/Hibernate Listing.isBestseller (Boolean) → listings.is_bestseller [smallint]: Boolean on smallint column: @JdbcTypeCode(SqlTypes.SMALLINT) (remove columnDefinition)
- `src/main/java/com/bobsusedbooks/entities/Listing.java:70` JPA/Hibernate Listing.isNewArrival (Boolean) → listings.is_new_arrival [smallint]: Boolean on smallint column: @JdbcTypeCode(SqlTypes.SMALLINT) (remove columnDefinition)
- `src/main/java/com/bobsusedbooks/entities/Order.java:54` JPA/Hibernate Order.shippedDate (LocalDate) → orders.shipped_date [timestamp without time zone]: date-only type on timestamp without time zone column: keep LocalDate + @JdbcTypeCode(SqlTypes.TIMESTAMP)
- `src/main/java/com/bobsusedbooks/entities/Order.java:57` JPA/Hibernate Order.deliveredDate (LocalDate) → orders.delivered_date [timestamp without time zone]: date-only type on timestamp without time zone column: keep LocalDate + @JdbcTypeCode(SqlTypes.TIMESTAMP)
- `src/main/java/com/bobsusedbooks/entities/Order.java:60` JPA/Hibernate Order.cancelledDate (LocalDate) → orders.cancelled_date [timestamp without time zone]: date-only type on timestamp without time zone column: keep LocalDate + @JdbcTypeCode(SqlTypes.TIMESTAMP)
- `src/main/java/com/bobsusedbooks/entities/PasswordResetToken.java:26` JPA/Hibernate PasswordResetToken.used (Boolean) → password_reset_tokens.used [smallint]: Boolean on smallint column: @JdbcTypeCode(SqlTypes.SMALLINT) (remove columnDefinition)
- `src/main/java/com/bobsusedbooks/entities/ShoppingCartItem.java:26` JPA/Hibernate ShoppingCartItem.isWishlistItem (Boolean) → shopping_cart_items.is_wishlist_item [smallint]: Boolean on smallint column: @JdbcTypeCode(SqlTypes.SMALLINT) (remove columnDefinition)

## C1. Type advisories (not blockers — review, change only if justified)

- `src/main/java/com/bobsusedbooks/entities/Book.java:34` Book.year (Integer) → books.year [bigint]: 32-bit field on bigint column — not a boot blocker; overflow risk pre-dates the migration. Widen only if values can exceed 2^31-1
- `src/main/java/com/bobsusedbooks/entities/Listing.java:39` Listing.quantity (Integer) → listings.quantity [bigint]: 32-bit field on bigint column — not a boot blocker; overflow risk pre-dates the migration. Widen only if values can exceed 2^31-1
- `src/main/java/com/bobsusedbooks/entities/Listing.java:49` Listing.status (Integer) → listings.status [bigint]: 32-bit field on bigint column — not a boot blocker; overflow risk pre-dates the migration. Widen only if values can exceed 2^31-1
- `src/main/java/com/bobsusedbooks/entities/OrderItem.java:30` OrderItem.quantity (Integer) → order_items.quantity [bigint]: 32-bit field on bigint column — not a boot blocker; overflow risk pre-dates the migration. Widen only if values can exceed 2^31-1
- `src/main/java/com/bobsusedbooks/entities/ShoppingCartItem.java:24` ShoppingCartItem.quantity (Integer) → shopping_cart_items.quantity [bigint]: 32-bit field on bigint column — not a boot blocker; overflow risk pre-dates the migration. Widen only if values can exceed 2^31-1

## B. Embedded SQL with source-dialect constructs

- `src/main/java/com/bobsusedbooks/demo/OracleBookRepository.java:36` — ROWNUM: `SELECT * FROM BOOKS b WHERE b.genre_id = ? AND ROWNUM <= 100 ORDER BY b.name`
- `src/main/java/com/bobsusedbooks/demo/OracleBookRepository.java:90` — NVL: `SELECT * FROM BOOKS b WHERE NVL(b.is_featured, 0) = 1 ORDER BY b.name`
- `src/main/java/com/bobsusedbooks/demo/OracleBookRepository.java:115` — DECODE: `SELECT b.*, DECODE(b.quantity, 0, 'Out of Stock', 1, 'Last Copy', 'In Stock') as stock_status FROM BOOKS b WHERE b.quantity < ? ORDER BY b.q`
- `src/main/java/com/bobsusedbooks/demo/OracleBookRepository.java:195` **(Tier-3 fragment)** — TO_DATE: `AND b.created_date > TO_DATE('2023-01-01', 'YYYY-MM-DD')`
- `src/main/java/com/bobsusedbooks/demo/OracleBookRepository.java:258` — ADD_MONTHS, SYSDATE: `SELECT b.* FROM ( SELECT b.*, ROW_NUMBER() OVER (ORDER BY SUM(s.quantity) DESC) as rank FROM BOOKS b JOIN SALES s ON b.id = s.book_id WHERE `
- `src/main/java/com/bobsusedbooks/demo/OracleBookService.java:36` — ADD_MONTHS, SYSDATE: `WITH customer_genres AS ( SELECT b.genre_id, COUNT(*) as purchase_count FROM orders o JOIN order_items oi ON o.id = oi.order_id JOIN books b`
- `src/main/java/com/bobsusedbooks/demo/OracleBookService.java:92` — LISTAGG, MONTHS_BETWEEN, SYSDATE: `SELECT c.id as customer_id, c.name as customer_name, COUNT(DISTINCT o.id) as total_orders, SUM(o.total_amount) as total_spent, AVG(o.total_a`
- `src/main/java/com/bobsusedbooks/repositories/BookRepository.java:97` — CONTAINS(, SCORE(: `SELECT b.* FROM BOOKS b WHERE CONTAINS(search_text, ?1, 1) > 0 ORDER BY SCORE(1) DESC`
- `src/main/java/com/bobsusedbooks/repositories/BookRepository.java:100` — CONTAINS(: `SELECT COUNT(*) FROM BOOKS b WHERE CONTAINS(search_text, ?1) > 0`
- `src/main/java/com/bobsusedbooks/services/BookService.java:181` **(Tier-3 fragment)** — full-text query syntax: fuzzy(: `fuzzy(`

## D. Stored-routine call sites

- `src/main/java/com/bobsusedbooks/repositories/CustomerRepository.java:34` — `@Query(value = "{ call get_customer_history(:customerId) }", nativeQuery = true)`

## E. Error-code handling

- `src/main/java/com/bobsusedbooks/utils/LoadCoverImages.java:48` — `} catch (SQLException e) {`

## A. Connection strings/URLs built in code

- `src/main/java/com/bobsusedbooks/config/DatabaseInfoConfig.java:49` — `String connectionDetails = jdbcUrl.split("@//")[1];`
- `src/main/java/com/bobsusedbooks/config/DatabaseInfoController.java:20` — `String connectionDetails = datasourceUrl.split("@//")[1];`

## A. Configuration

- `pom.xml:48` — `<groupId>org.postgresql</groupId>`
- `pom.xml:49` — `<artifactId>postgresql</artifactId>`
- `pom.xml:55` — `<artifactId>ojdbc17</artifactId>`
- `src/main/resources/application.properties:2` — `spring.datasource.url=jdbc:oracle:thin:@//<ORACLE_HOST>:1521/ORCL`
- `src/main/resources/application.properties:4` **(plaintext-secret)** — `spring.datasource.password=***`
- `src/main/resources/application.properties:5` — `spring.datasource.driver-class-name=oracle.jdbc.OracleDriver`
- `src/main/resources/application.properties:9` — `spring.jpa.hibernate.ddl-auto=validate`
- `src/main/resources/application.properties:12` — `spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.OracleDialect`

## F. Result-set typing

- `src/main/java/com/bobsusedbooks/demo/OracleBookRepository.java:294` — `book.setId(rs.getLong("id"));`
- `src/main/java/com/bobsusedbooks/demo/OracleBookRepository.java:295` — `book.setTitle(rs.getString("name"));`
- `src/main/java/com/bobsusedbooks/demo/OracleBookRepository.java:296` — `book.setAuthor(rs.getString("author"));`
- `src/main/java/com/bobsusedbooks/demo/OracleBookRepository.java:297` — `book.setIsbn(rs.getString("isbn"));`
- `src/main/java/com/bobsusedbooks/demo/OracleBookService.java:139` — `book.setId(rs.getLong("id"));`
- `src/main/java/com/bobsusedbooks/demo/OracleBookService.java:140` — `book.setTitle(rs.getString("name"));`
- `src/main/java/com/bobsusedbooks/demo/OracleBookService.java:141` — `book.setAuthor(rs.getString("author"));`
- `src/main/java/com/bobsusedbooks/demo/OracleBookService.java:142` — `book.setIsbn(rs.getString("isbn"));`

## H. Source-engine SQL scripts

- `src/main/resources/db/oracle/01_user.sql` (560 bytes) — no construct hits
- `src/main/resources/db/oracle/02_schema_oracle_v2.sql` (8223 bytes) — NVL
- `src/main/resources/db/oracle/04_complex_schema_v2.sql` (16781 bytes) — FETCH FIRST, NVL, REGEXP_, SYSDATE, SYSTIMESTAMP, TRUNC
- `src/main/resources/db/oracle/demo_cleanup.sql` (2253 bytes) — no construct hits
- `src/main/resources/db/oracle/reload_data.sql` (1541 bytes) — no construct hits

## Flagged files (open these; the rest had no hits)

- `pom.xml`
- `src/main/java/com/bobsusedbooks/config/DatabaseInfoConfig.java`
- `src/main/java/com/bobsusedbooks/config/DatabaseInfoController.java`
- `src/main/java/com/bobsusedbooks/demo/OracleBookRepository.java`
- `src/main/java/com/bobsusedbooks/demo/OracleBookService.java`
- `src/main/java/com/bobsusedbooks/entities/Address.java`
- `src/main/java/com/bobsusedbooks/entities/Book.java`
- `src/main/java/com/bobsusedbooks/entities/BookCover.java`
- `src/main/java/com/bobsusedbooks/entities/Customer.java`
- `src/main/java/com/bobsusedbooks/entities/Listing.java`
- `src/main/java/com/bobsusedbooks/entities/Order.java`
- `src/main/java/com/bobsusedbooks/entities/PasswordResetToken.java`
- `src/main/java/com/bobsusedbooks/entities/ShoppingCartItem.java`
- `src/main/java/com/bobsusedbooks/repositories/BookRepository.java`
- `src/main/java/com/bobsusedbooks/repositories/CustomerRepository.java`
- `src/main/java/com/bobsusedbooks/repositories/OrderRepository.java`
- `src/main/java/com/bobsusedbooks/repositories/ShoppingCartRepository.java`
- `src/main/java/com/bobsusedbooks/services/BookService.java`
- `src/main/java/com/bobsusedbooks/utils/LoadCoverImages.java`
- `src/main/resources/application.properties`

Limits: static scanning cannot see SQL assembled from configuration/the database or generated by ORM criteria/LINQ; an ORM app with zero SQL text can still break (identifier case, types). The boot against the migrated target (Validation) is the proof.
