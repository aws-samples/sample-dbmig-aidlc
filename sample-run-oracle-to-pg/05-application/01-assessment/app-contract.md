# App Contract — what the DEMO migration changed that this app must follow

Derived from the migration's own artifacts, not generic rules. Each row cites its source.

| # | DB change | Required app change | Source |
|---|---|---|---|
| 1 | Target is Aurora PostgreSQL 17.7, db `demodb`, schema `demo` | JDBC URL → `jdbc:postgresql://aurora-cluster.example.com:5432/demodb?currentSchema=demo&sslmode=require`; driver → `org.postgresql.Driver` | `00-intake/intake.md`, `app-config.yaml` |
| 2 | Hibernate dialect no longer Oracle | remove `hibernate.dialect=OracleDialect` (Hibernate 6 auto-detects PG) | `app-config.yaml` §target.jdbc |
| 3 | Identifiers folded UPPER→lower, unquoted | JPA `@Table/@Column` names are already lower-case & unquoted → **no change**; verified against `02-construction/ddl/demo/*.sql` | conversion-log §identifiers |
| 4 | Oracle Text → GIN full-text (`to_tsvector @@ to_tsquery`), `SCORE(1)` → `ts_rank` | rewrite `BookRepository.fullTextSearchBooks` query + countQuery; prefer `plainto_tsquery` for user input | validation-summary carry-forward #1; conversion-log §full-text |
| 5 | Packages flattened; `get_customer_history` — **verify actual target shape** in `code-manifest-DEMO.yaml` (standalone procs kept names; `{ call … }` works only for PROCEDUREs) | `CustomerRepository.getCustomerPurchaseHistory` call site must match the converted routine's shape | validation-summary carry-forward #4; code-manifest |
| 6 | `ORA-20001/20002` → SQLSTATE `U0001`/`U0002` | any error-code branching must switch (inventory found **none** in app code) | validation-summary carry-forward #2 |
| 7 | 4 procedures lost internal `COMMIT` — caller owns txn | verify `@Transactional` on call sites (only #5's call site exists) | validation-summary carry-forward #3 |
| 8 | `DATE`→`timestamp(0)`, `NUMBER(19,0)`→`bigint`, `NUMBER(1,0)`→`smallint` 0/1 | entities already use `Long`/`LocalDateTime`/`Integer` 0/1 → spot-check only; `COUNT(*)` now `bigint` | conversion-log §datatypes |
| 9 | Oracle dialect SQL in raw-JDBC demo classes (`ROWNUM`, `NVL`, `DECODE`, `TO_DATE`, `ADD_MONTHS`, `SYSDATE`, `MONTHS_BETWEEN`) | rewrite per `app-sql-rules.md` §1–2 | app-sql-rules.md |

**Important verification from the migration workspace:** `get_customer_history` is NOT in the
DEMO code manifest (20 units: 5 functions, 5 procedures ×2 manifest rows, 5 packages+bodies —
named list checked). The Oracle source never had it either — the app calls a routine that does
not exist in the migrated schema. → **blocked item, needs a decision**, not a silent fix.
