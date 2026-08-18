# Conversion Log — JavaBobsUsedBooks → PostgreSQL

Backups: `05-application/backup/<run-timestamp>/` (mirrored tree, 7 files + MANIFEST).
**Zero `.bak` files created in the application.**

## Changes applied (per change-plan.md)

| Site | File | Change | Class |
|---|---|---|---|
| 4 | `application.properties` | Oracle URL/driver → PostgreSQL (`currentSchema=demo&sslmode=require`); dialect line removed (Hibernate 6 auto-detects); **plaintext password → `${DB_PASSWORD}` env reference** | mechanical |
| 5 | `pom.xml` | `ojdbc17` dependency removed (`postgresql` already present) | mechanical |
| 1 | `BookRepository.java` | `CONTAINS/SCORE` → `@@ plainto_tsquery` + `ts_rank` (main + countQuery); table `BOOKS`→`books` | **BEHAVIOURAL** |
| 2 | `demo/OracleBookRepository.java` | `ROWNUM <= 100` + `ORDER BY` → `ORDER BY … LIMIT 100` | **BEHAVIOURAL** (intent-preserving; Oracle capped before sort) |
| B3 | same | `NVL` → `coalesce` | mechanical |
| B4 | same | `DECODE` → simple `CASE` | mechanical |
| B5 | same | `TO_DATE(literal)` → `DATE '2023-01-01'` (tier-3 stmt reconstructed) | mechanical |
| B6 | same | `ADD_MONTHS(SYSDATE,-12)` → interval; alias `rank` → `sales_rank` | mechanical |
| B7 | `demo/OracleBookService.java` | `ADD_MONTHS(SYSDATE,-6)` → interval | mechanical |
| B8 | same | timestamp-subtraction AVG → `EXTRACT(EPOCH …)/86400`; `LISTAGG…WITHIN GROUP` → `string_agg`; `MONTHS_BETWEEN` → epoch months (approximation flagged) | mechanical (+1 flagged approximation) |
| +2 | `config/DatabaseInfoConfig.java`, `config/DatabaseInfoController.java` | URL parser split on Oracle-only `@//` → generic `://…?` split; **fallback no longer echoes the raw URL (could leak credentials)** | mechanical (+security fix) |

## Found during Construction (inventory miss, honestly recorded)

The residual sweep caught `DatabaseInfoConfig`/`DatabaseInfoController` parsing the JDBC URL with
an Oracle-specific `@//` split — missed by the inventory because the scan terms were SQL
constructs, not URL formats. Backed up into the same run and fixed. Lesson recorded: inventory
category A should also grep for `jdbc:` parsing in code, not just config files.

## Deliberately NOT changed

- `CustomerRepository.getCustomerPurchaseHistory` — **BLOCKED**: `get_customer_history` exists in
  neither the Oracle source nor the target (verified 4 ways). Needs a product decision
  (implement / rewrite as query / delete). Left as-is; compiles.
- `db/oracle/*.sql` seed scripts — out of scope.
- 5 pre-existing `.bak` files — reported, not touched.
- JPA entities — verified already lower-case/unquoted; no edits needed.
- `BookRepository` advanced-search `||` concatenations — NULL-guarded by `IS NULL OR`
  short-circuits; considered and intentionally unchanged.
