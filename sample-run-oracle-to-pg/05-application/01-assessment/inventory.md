# Application Inventory — JavaBobsUsedBooks (Inception assessment)

## Summary

| Category | Sites | Files | Mechanical | Behavioural | Blocked |
|---|---|---|---|---|---|
| A. Connectivity/config | 4 keys | 1 + pom.xml | 4 | 0 | 0 |
| B. Embedded SQL | 11 statements | 3 | 8 | 3 | 0 |
| C. Entity mappings | 0 (verified clean) | — | — | — | — |
| D. Stored-routine call sites | 1 | 1 | 0 | 0 | **1** |
| E. Error handling | 0 found | — | — | — | — |
| F. Result-set typing | 1 (`getInt("quantity")` OK; counts use JPA) | — | 0 | 0 | 0 |
| G. Schema-qualified refs | 0 | — | — | — | — |
| H. Build dependencies | 2 (`ojdbc17` remove, `postgresql` already present) | pom.xml | 2 | 0 | 0 |

## B. Embedded SQL detail

| # | File:Line | Tier | Constructs | Class |
|---|---|---|---|---|
| B1 | `repositories/BookRepository.java:96-101` | 2 (annotation) | `CONTAINS(search_text,?1,1)>0`, `ORDER BY SCORE(1) DESC`, countQuery `CONTAINS` | **BEHAVIOURAL** (full-text redesign; term syntax + ranking change) |
| B2 | `demo/OracleBookRepository.java:35-44` | 2 | `ROWNUM <= 100` (with `ORDER BY` in same stmt) | **BEHAVIOURAL** (`ROWNUM` before sort vs `LIMIT` after) |
| B3 | `demo/OracleBookRepository.java:91` | 2 | `NVL(b.is_featured,0)=1` | mechanical |
| B4 | `demo/OracleBookRepository.java:114-121` | 2 | `DECODE(b.quantity,…)` | mechanical |
| B5 | `demo/OracleBookRepository.java:155-195` | **3** (StringBuilder) | dynamic WHERE + `TO_DATE('2023-01-01','YYYY-MM-DD')` | mechanical (statement reconstructed — fixed literal, appended unconditionally) |
| B6 | `demo/OracleBookRepository.java:263` | 2 | `ADD_MONTHS(SYSDATE,-12)` | mechanical |
| B7 | `demo/OracleBookService.java:42` | 2 | `ADD_MONTHS(SYSDATE,-6)` | mechanical |
| B8 | `demo/OracleBookService.java:101` | 2 | `ROUND(MONTHS_BETWEEN(SYSDATE,MIN(o.order_date)))` | mechanical |
| B9 | `repositories/BookRepository.java:75-83` | 2 | `UPPER(… \|\| :keyword \|\| …)` LIKE patterns | **BEHAVIOURAL** (NULL propagation in `\|\|` — Oracle treats NULL as `''`) |
| B10 | pom.xml `ojdbc17` dependency | H | — | mechanical |
| B11 | `application.properties` (4 keys) | A | Oracle URL/driver/dialect + **plaintext password** | mechanical (+ secret-handling note) |

## D. Stored-routine call site

`repositories/CustomerRepository.java:34` — `{ call get_customer_history(:customerId) }`.
**BLOCKED:** verified against the migration manifest, the converted code, the Oracle source AND
the live target — the routine exists **nowhere**. The app ships a call to a procedure that was
never in the database. Options at the gate: (a) implement it on the target (out of this module's
scope — a construction-phase item), (b) rewrite the method as a JPQL/native query over
orders/order_items, (c) remove the dead method. Decision needed; not converted silently.

## Not-a-target (report, don't touch)

- 5 stray `.bak` files from a previous ad-hoc conversion — incl. `target/classes/...` (stale build
  output) and 4 under `src/`. Recommend deletion in a separate cleanup; this module will not
  create more of these (mirrored backups instead).
- `src/main/resources/db/oracle/*.sql` — Oracle seed/DBA scripts, out of scope (DB side already
  migrated by the DB phases).
- `demo/Oracle*` classes query a `sales` table that exists in **neither** the Oracle DEMO schema
  nor the target — pre-existing dead code against a phantom table (runs only via the demo
  controller). SQL converted anyway (it is in scope), but flagged: it will fail at runtime on
  both engines equally.

## Coverage caveat

Static scan only. No MyBatis/mappers, no `.sql` resources outside `db/oracle/`, no dynamic SQL
from config detected. The `src/test` suite will be run at Validation.
