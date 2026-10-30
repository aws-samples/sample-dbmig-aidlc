# Inventory — JavaBobsUsedBooks (from `app-scan.md`, flagged files read)

119 files scanned, 20 flagged; 13 JPA entities, **128 mapped fields checked against the live `demo` schema**; 0 mapping issues.

| Category | Sites | Class |
|---|---|---|
| A. config | `application.properties` (URL, driver, dialect, **plaintext password**), `pom.xml` (ojdbc17) | mechanical + security |
| A. URL parsing in code | `DatabaseInfoConfig`, `DatabaseInfoController` split on Oracle `@//`; fallback echoes the raw URL | mechanical + security |
| A. utility reading config | `utils/LoadCoverImages` reads `application.properties` with `java.util.Properties` (no `${…}` resolution) | **new finding**: externalised placeholders would reach `DriverManager` verbatim |
| B. dialect SQL | `BookRepository.fullTextSearchBooks` (CONTAINS/SCORE, Tier 2 over 3 lines); `BookService.prepareSearchQuery` builds `fuzzy(t, 40) OR …` (Tier 3); `demo/OracleBookRepository` (ROWNUM, NVL, DECODE, TO_DATE, ADD_MONTHS); `demo/OracleBookService` (ADD_MONTHS, LISTAGG, MONTHS_BETWEEN) | behavioural (search), mechanical (demo) |
| C1. type fixes | 10 `Boolean` on `smallint`, 5 `LocalDate` on `timestamp(0)`, 1 `@Lob byte[]` on `bytea` | required |
| C1. advisories | 5 `Integer` on `bigint` | no change (validate accepts; NUMBER(10) already exceeded int32) |
| D. routine calls | `CustomerRepository` `{ call get_customer_history }` | pre-existing broken |
| E. error codes | `LoadCoverImages` catches `SQLException` and prints the message only | no change |
| F. result-set typing | `LoadCoverImages` `rs.getInt(1)` on `COUNT(*)` (bigint) — pgjdbc converts; demo classes read `name` columns that do not exist | no change / pre-existing |

**Pre-existing broken (C2, source catalog evidence, 2026-10-30):** `ALL_OBJECTS` has no `GET_CUSTOMER_HISTORY`;
`ALL_TABLES` has no `SALES`; `ALL_TAB_COLUMNS` has none of BOOKS.NAME/QUANTITY/PRICE/IS_AVAILABLE/AVERAGE_RATING/
CREATED_DATE/IS_FEATURED, CUSTOMERS.NAME, ORDERS.ORDER_DATE → `demo/OracleBookRepository`, `demo/OracleBookService`
and the `get_customer_history` call fail on the source too.

**Not targets:** 4 `.bak` leftovers; `src/main/resources/db/oracle/*.sql` (source-engine scripts, out of scope).

**Carry-forwards:** `fulltext_redesign` → the two search sites above; LOW_COVERAGE order/cart paths (untested on real data in the DB run too).

**Coverage caveat:** static scanning cannot see SQL built from configuration or JPA criteria; the boot with
`ddl-auto=validate` and the smoke requests in Validation are the proof.
