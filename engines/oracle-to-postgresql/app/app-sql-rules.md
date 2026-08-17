# App-layer SQL rules — Oracle → PostgreSQL

Rules for SQL **embedded in application code** (repositories, DAOs, mappers, annotations,
string concatenation, `.sql` resources). Schema and stored-code conversion is handled by the
construction phase; this file covers only what lives in the application.

Two classes, handled differently:

- **Mechanical** — dialect syntax. Convert directly.
- **Behavioural** — compiles and runs but can return *different results*. Convert **and** raise
  it in the change plan with the risk stated. Never bury one of these in a diff.

---

## 1. Mechanical rewrites

| Oracle | PostgreSQL | Note |
|---|---|---|
| `SYSDATE` | `CURRENT_TIMESTAMP` / `LOCALTIMESTAMP` | confirm time-zone intent |
| `SYSTIMESTAMP` | `CURRENT_TIMESTAMP` | |
| `NVL(a,b)` | `COALESCE(a,b)` | |
| `NVL2(a,b,c)` | `CASE WHEN a IS NOT NULL THEN b ELSE c END` | |
| `DECODE(e,k,v,…,d)` | `CASE WHEN e = k THEN v … ELSE d END` | `k = NULL` must become `IS NULL` |
| `FROM DUAL` | omit the clause | |
| `\|\|` concat | `\|\|` (unchanged) | but see §2 NULL concat |
| `SUBSTR/INSTR/LENGTH` | `substr` / `position`/`strpos` / `length` | `INSTR` with 3+ args needs a rewrite |
| `TO_DATE(s,fmt)` | `to_timestamp(s,fmt)::timestamp` | `to_date` returns `date` and drops time |
| `TO_CHAR(d,fmt)` | `to_char(d,fmt)` | format masks mostly align — see §2 |
| `ADD_MONTHS(d,n)` | `d + n * INTERVAL '1 month'` | |
| `MONTHS_BETWEEN` | arithmetic, or `orafce` | |
| `TRUNC(d)` | `date_trunc('day', d)` or `d::date` | not a no-op — see §2 |
| `d + n` (n days) | `d + n * INTERVAL '1 day'` | bare `+ n` fails on timestamp |
| `LISTAGG(x,d) WITHIN GROUP (ORDER BY y)` | `string_agg(x, d ORDER BY y)` | |
| `MINUS` | `EXCEPT` | |
| `(+)` outer join | ANSI `LEFT/RIGHT JOIN` | |
| `CONNECT BY PRIOR` | recursive CTE | `CONNECT BY LEVEL` → `generate_series` |
| `seq.NEXTVAL` | `nextval('seq')` | prefer `RETURNING id` |
| `/*+ hint */` | remove | re-tune on the target |
| `FETCH FIRST n ROWS ONLY` | `LIMIT n` | |
| `REGEXP_LIKE(x,p)` | `x ~ p` | |
| `REGEXP_REPLACE(x,p,r)` | `regexp_replace(x,p,r,'g')` | **`'g'` is required** — PG replaces only the first match without it |

---

## 2. Behavioural differences — convert AND flag

Each of these compiles cleanly and changes results silently. Every occurrence belongs in the
change plan with its risk, and in the final report with a review owner.

- **`ROWNUM` + `ORDER BY`.** Oracle applies `ROWNUM` **before** sorting; `LIMIT` applies
  **after**. `WHERE ROWNUM <= 10 ORDER BY x` is *not* `ORDER BY x LIMIT 10`. Reconstruct the
  intent, and never convert a `ROWNUM` fragment without seeing the whole statement.
- **Empty string vs NULL.** `''` is NULL in Oracle but a real value in PostgreSQL. Review every
  `IS NULL`, `= ''`, and concatenation on nullable text columns.
- **NULL in concatenation.** Oracle treats NULL as `''` in `||`, PostgreSQL propagates NULL, so
  `a || ' ' || b` becomes NULL when either side is NULL. Wrap operands in `COALESCE(...,'')` to
  preserve Oracle behaviour.
- **`TRUNC(date)` was doing work.** It strips the time component from an Oracle `DATE`. If the
  column mapped to `timestamp`, `date_trunc('day', …)` is still required — dropping it changes
  comparisons.
- **`TO_CHAR`/`TO_DATE` format masks.** `MI` is minutes, `MM` is months; `HH24`; `MON`/`DAY`
  depend on `lc_time`. A wrong mask corrupts data silently rather than erroring.
- **Sort order and collation.** Oracle's `NLS_SORT` and PostgreSQL's collation differ, as does
  default NULL placement. Add explicit `NULLS FIRST`/`NULLS LAST` where order is contractual.
- **Implicit type coercion.** Oracle silently compares `VARCHAR2` to `NUMBER`; PostgreSQL raises
  `operator does not exist`. Add an explicit cast — and note casting text→numeric now *errors*
  on non-numeric data that Oracle tolerated. That makes it a data-quality question.
- **`COUNT(*)` returns `bigint`.** Java `int` / .NET `Int32` assignments throw or truncate.
- **Result-set column case.** Oracle metadata is UPPERCASE, PostgreSQL folds to lower.
  `rs.getX("COL")` lookups break. Prefer explicit aliases in the SQL.
- **Locking.** `FOR UPDATE NOWAIT` → `FOR UPDATE NOWAIT` (supported); `SKIP LOCKED` is supported
  from PG 9.5. Oracle's `FOR UPDATE WAIT n` has no equivalent — use `lock_timeout`.

---

## 3. Full-text search — the redesign that reaches the app layer

Oracle Text is a schema feature, but its **query syntax lives in application code**, so the app
must change in step with the schema.

| Oracle (app code) | PostgreSQL |
|---|---|
| `CONTAINS(col, :terms) > 0` | `to_tsvector('english', coalesce(col,'')) @@ to_tsquery('english', :terms)` |
| `CONTAINS(col, :terms, 1) > 0` … `ORDER BY SCORE(1) DESC` | `… @@ to_tsquery(...)` … `ORDER BY ts_rank(to_tsvector('english', coalesce(col,'')), to_tsquery('english', :terms)) DESC` |
| `CATSEARCH(col, :terms, NULL) > 0` | same `@@` form |

Behavioural notes that must be flagged, not assumed:

- **Query-term syntax differs.** Oracle Text accepts `word1 AND word2`, `word1 NEAR word2`,
  `word*`. `to_tsquery` requires `&`, `|`, `!`, `<->` and rejects bare spaces — a user typing
  two words raises a syntax error. Use **`plainto_tsquery`** (treats input as plain words,
  AND-ed) or **`websearch_to_tsquery`** (supports quotes and `-exclusion`, never raises) for
  free-text boxes. This is usually the correct choice for a UI search field.
- **Stopwords.** `to_tsvector('english', …)` strips English stopwords, so `the` matches nothing.
  Oracle's default lexer behaves similarly, but confirm against the app's expectations.
- **Ranking is not `SCORE`.** `ts_rank`/`ts_rank_cd` produce different magnitudes and ordering
  than Oracle's `SCORE(n)`. Relative ordering is usually similar; absolute values are not
  comparable, so any UI displaying a score needs review.
- The index must exist on the target (`USING gin (to_tsvector(...))`) **and the query expression
  must match it exactly**, or the planner silently falls back to a sequential scan. Verify with
  `EXPLAIN`.

---

## 4. Stored-routine call sites

- **Package flattening.** `PKG.PROC(...)` → `<pkg>_<subprogram>(...)`. Read the migration's
  conversion log for the actual names; do not re-derive them.
- **Procedure vs function call shape.** JDBC `{ call p(?) }` works for a PostgreSQL `PROCEDURE`.
  If the routine was converted to a **function**, the call must become `SELECT * FROM f(?)` or
  `SELECT f(?)`. Getting this wrong yields a runtime `is not a procedure` error.
- **`OUT` parameters.** PostgreSQL procedures return OUT values as a result row (PG 14+);
  `CallableStatement.registerOutParameter` still works via JDBC, but a routine converted to
  `RETURNS TABLE` must be consumed as a result set instead.
- **Ref cursors.** An Oracle `SYS_REFCURSOR` OUT parameter becomes a `refcursor` that must be
  fetched inside the same transaction — or, preferably, a set-returning function consumed as a
  normal query.
- **Transaction ownership.** Where the migration removed a procedure's internal `COMMIT`, the
  caller is now responsible. Confirm `@Transactional` (or an explicit commit) wraps the call, or
  writes will be silently rolled back at connection close.

---

## 5. ORM / framework specifics

- **Hibernate/JPA dialect** → `org.hibernate.dialect.PostgreSQLDialect`. On Hibernate 6 the
  dialect is auto-detected, so removing the property is often better than swapping it.
- **`@Table` / `@Column` names.** Oracle DDL is UPPERCASE; PostgreSQL folds unquoted names to
  lower. Unquoted JPA names work either way, but a **quoted** `@Column(name = "\"MY_COL\"")`
  pins the old case and will break. Check for quoted identifiers.
- **`@SequenceGenerator`** referencing an Oracle sequence must point at the target sequence, or
  switch to `GenerationType.IDENTITY` where the migration used `GENERATED … AS IDENTITY`.
- **`ddl-auto`.** Keep `validate` (or `none`). Never let `update`/`create` run against a
  freshly-migrated schema — it will silently alter the converted DDL.
- **Native-query pagination.** Spring Data appends `LIMIT/OFFSET` for native queries; an
  Oracle-specific `ROWNUM` wrapper in the query text must be removed so it does not conflict.
- **Flyway/Liquibase.** Oracle-specific migration scripts under `db/oracle/` (or equivalent) are
  not converted by this module unless in scope — flag them, and point Flyway at a target-specific
  location rather than editing history in place.

---

## 6. What this module does NOT convert

- Standalone stored procedures, packages and functions living **in the database** — those are the
  construction phase's job (`db-migration-construction`).
- Schema DDL.
- Oracle-specific admin/DBA scripts shipped with the app (flag them instead).
