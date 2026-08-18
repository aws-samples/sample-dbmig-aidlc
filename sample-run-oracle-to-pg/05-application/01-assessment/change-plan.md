# Change Plan — JavaBobsUsedBooks → PostgreSQL (demodb.demo)

**Nothing has been edited yet.** This plan is the Inception gate artifact; conversion begins only
on approval. *(For this test run the user pre-approved execution — "you can test freely" — which
is recorded here as the gate approval.)*

**Scope:** 6 files (5 source + pom.xml), 15 edit sites. Excluded: `target/`, static assets,
`db/oracle/*.sql` seed scripts, the 5 pre-existing `.bak` files.
**Backups to:** `migrations/demo/05-application/backup/<timestamp>/` (mirrored tree).
**Verification:** `mvn -q -B clean compile` then `mvn -q -B test`; PREPARE converted SQL against
the live target (read-only) where identifiers allow.

---

## BEHAVIOURAL changes (review these first)

### 1. repositories/BookRepository.java:96–101  [BEHAVIOURAL — full-text redesign]
Current:
```java
"SELECT b.* FROM BOOKS b " +
"WHERE CONTAINS(search_text, ?1, 1) > 0 " +
"ORDER BY SCORE(1) DESC",
countQuery = "SELECT COUNT(*) FROM BOOKS b WHERE CONTAINS(search_text, ?1) > 0",
```
Proposed:
```java
"SELECT b.* FROM books b " +
"WHERE to_tsvector('english', coalesce(b.search_text,'')) @@ plainto_tsquery('english', ?1) " +
"ORDER BY ts_rank(to_tsvector('english', coalesce(b.search_text,'')), plainto_tsquery('english', ?1)) DESC",
countQuery = "SELECT COUNT(*) FROM books b WHERE to_tsvector('english', coalesce(b.search_text,'')) @@ plainto_tsquery('english', ?1)",
```
Why: DB migration redesigned Oracle Text → GIN (`conversion-log.md` §full-text; carry-forward #1).
Risk: `plainto_tsquery` chosen (not `to_tsquery`) because the input is a raw UI search string —
`to_tsquery` raises on bare spaces. Ranking is `ts_rank`, not comparable to Oracle `SCORE` in
magnitude; relative order generally similar. English stopwords match nothing. The expression
matches the GIN index expression exactly (verified in DDL), so the index is used.

### 2. demo/OracleBookRepository.java:35–44  [BEHAVIOURAL — ROWNUM with ORDER BY]
Current: `WHERE b.genre_id = ? AND ROWNUM <= 100 … ORDER BY b.title` (single statement)
Proposed: `WHERE b.genre_id = ? … ORDER BY b.title LIMIT 100`
Why: `ROWNUM` has no PG equivalent (`app-sql-rules.md` §2).
Risk: **semantics change deliberately** — Oracle capped 100 rows *before* sorting (arbitrary 100,
then sorted); `LIMIT` returns the *first 100 by title*. The Oracle behaviour is almost certainly
the bug and the LIMIT form the intent, but this is a results-visible change. FLAGGED.

### 3. repositories/BookRepository.java:75–83  [BEHAVIOURAL — NULL in ||]
Current: `UPPER(b.title) LIKE UPPER('%' || :keyword || '%')` (and 2 similar)
Proposed: unchanged text — but guarded by the existing `:keyword IS NULL OR` short-circuit.
Why/Risk: Oracle treats NULL as `''` in `||`; PG propagates NULL. Here every concat is behind an
`IS NULL OR` guard, so NULL never reaches the concat → **no edit needed**; recorded so the
reviewer sees it was considered, not missed.

## Mechanical changes

### 4. application.properties (4 keys)
`spring.datasource.url` → `jdbc:postgresql://aurora-cluster.example.com:5432/demodb?currentSchema=demo&sslmode=require`
`driver-class-name` → `org.postgresql.Driver`; `hibernate.dialect` line **removed** (Hibernate 6
auto-detects); username stays `demo`… **credential note:** current file has a plaintext password;
we will reference `${DB_PASSWORD}` and document it (never echo the value).
Risk: none — config only. `ddl-auto=validate` retained (correct against a migrated schema).

### 5. pom.xml — remove `ojdbc17`
`postgresql` driver already present. Risk: none; demo classes use `DataSource`, not Oracle APIs.

### 6–11. demo/Oracle*.java mechanical SQL (6 sites)
- `NVL(b.is_featured, 0) = 1` → `coalesce(b.is_featured, 0) = 1`
- `DECODE(b.quantity, 0,'Out of Stock', …)` → `CASE b.quantity WHEN 0 THEN 'Out of Stock' … END`
- `TO_DATE('2023-01-01','YYYY-MM-DD')` → `DATE '2023-01-01'`
- `ADD_MONTHS(SYSDATE,-12)` → `CURRENT_TIMESTAMP - INTERVAL '12 months'` (and `-6` variant)
- `ROUND(MONTHS_BETWEEN(SYSDATE, MIN(o.order_date)))` →
  `ROUND(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MIN(o.order_date))) / 2629746)` — flagged minor:
  month-length averaging vs Oracle's calendar months; demo-only code.
Risk: none — syntax only (tier-3 site B5 reconstructed: literal is appended unconditionally).

## BLOCKED (decision needed — not converted)

### 12. repositories/CustomerRepository.java:34
`{ call get_customer_history(:customerId) }` — routine exists **nowhere**: not in the Oracle
source, not in the migration manifest, not on the target (all four checked). Options:
(a) implement it on the target (construction-phase work), (b) rewrite as a JPQL query over
orders/order_items, (c) delete the dead method + its DTO usage.
**For this test run: leave unchanged** and record — it compiled before and still compiles (JPA
parses it lazily), so it does not block the build.

## Out-of-scope notes for the reviewer
- `demo/Oracle*` classes reference a `sales` table absent from BOTH engines (pre-existing dead
  code). Converted anyway (in scope), fails identically at runtime on either engine.
- 5 stray `.bak` files recommended for deletion in a separate cleanup.
