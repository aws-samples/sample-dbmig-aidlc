# App-layer SQL rules — Oracle → MySQL

Rules for SQL **embedded in application code**. Schema and stored-code conversion belongs to the
construction phase; this file covers only the application.

**Mechanical** = dialect syntax, convert directly. **Behavioural** = compiles and runs but can
return different results — convert **and** raise it in the change plan.

---

## 1. Mechanical rewrites

| Oracle | MySQL | Note |
|---|---|---|
| `SYSDATE` / `SYSTIMESTAMP` | `NOW(6)` | `CURRENT_TIMESTAMP` also works |
| `NVL(a,b)` | `IFNULL(a,b)` / `COALESCE(a,b)` | |
| `NVL2(a,b,c)` | `IF(a IS NOT NULL, b, c)` | |
| `DECODE(e,k,v,…,d)` | `CASE WHEN e = k THEN v … ELSE d END` | |
| `FROM DUAL` | `FROM DUAL` is valid, or omit | MySQL accepts `DUAL` |
| `a \|\| b` | `CONCAT(a,b)` | **`\|\|` is OR in MySQL by default** — see §2 |
| `SUBSTR/INSTR/LENGTH` | `SUBSTRING`/`INSTR`/`CHAR_LENGTH` | `LENGTH` is bytes in MySQL, use `CHAR_LENGTH` |
| `TO_DATE(s,fmt)` | `STR_TO_DATE(s,fmt)` | **format masks differ entirely** — see §2 |
| `TO_CHAR(d,fmt)` | `DATE_FORMAT(d,fmt)` | `%Y-%m-%d` style, not `YYYY-MM-DD` |
| `TRUNC(d)` | `DATE(d)` | |
| `ADD_MONTHS(d,n)` | `DATE_ADD(d, INTERVAL n MONTH)` | |
| `MONTHS_BETWEEN(a,b)` | `TIMESTAMPDIFF(MONTH,b,a)` | |
| `d + n` (days) | `DATE_ADD(d, INTERVAL n DAY)` | |
| `LISTAGG(x,d) WITHIN GROUP (ORDER BY y)` | `GROUP_CONCAT(x ORDER BY y SEPARATOR d)` | note `group_concat_max_len` |
| `MINUS` | `LEFT JOIN … WHERE … IS NULL` | MySQL has no `EXCEPT` before 8.0.31 |
| `(+)` outer join | ANSI `LEFT/RIGHT JOIN` | |
| `CONNECT BY PRIOR` | recursive CTE (`WITH RECURSIVE`, 8.0+) | |
| `seq.NEXTVAL` | `AUTO_INCREMENT` + `LAST_INSERT_ID()` | no sequences |
| `ROWNUM <= n` | `LIMIT n` | see §2 for the `ORDER BY` case |
| `FETCH FIRST n ROWS ONLY` | `LIMIT n` | |
| `/*+ hint */` | remove (MySQL hints differ) | re-tune |
| `REGEXP_LIKE(x,p)` | `x REGEXP p` | escape backslashes for the string literal |
| `RETURNING id INTO` | `LAST_INSERT_ID()` after the insert | |

---

## 2. Behavioural differences — convert AND flag

- **`||` means OR, not concatenation.** Unless `sql_mode` includes `PIPES_AS_CONCAT`, Oracle's
  `a || b` silently becomes a boolean OR in MySQL — numeric `0`/`1` instead of a string, with no
  error. Always rewrite to `CONCAT(...)`. This is the single most dangerous mechanical-looking
  change in this pair.
- **`CONCAT` and NULL.** Oracle treats NULL as `''` in concatenation; MySQL's `CONCAT` returns
  **NULL** if any argument is NULL. Wrap arguments in `IFNULL(x,'')` to preserve Oracle behaviour.
- **Date format masks are a different language.** `TO_DATE(s,'DD/MM/YYYY')` →
  `STR_TO_DATE(s,'%d/%m/%Y')`. A mask copied across unchanged either errors or, worse, parses to
  the wrong date. Check every mask individually.
- **`ROWNUM` + `ORDER BY`.** Oracle limits before sorting, `LIMIT` applies after. Reconstruct the
  intent; never convert a `ROWNUM` fragment without the whole statement.
- **Empty string vs NULL.** `''` is NULL in Oracle, a real value in MySQL. Review `IS NULL`,
  `= ''` and NOT NULL columns.
- **Implicit coercion is permissive in *both*, with different rules.** MySQL silently converts a
  non-numeric string to `0` in a numeric comparison rather than erroring. A mismatched join that
  "worked" in Oracle can return *different rows* in MySQL with no diagnostic — more dangerous than
  PostgreSQL's refusal. Add explicit `CAST`s and treat it as a data-quality finding.
- **Case sensitivity.** String comparison follows the column's collation: the common
  `utf8mb4_0900_ai_ci` is **case-insensitive**, so `WHERE name = 'ABC'` now matches `'abc'` —
  Oracle's default was case-sensitive. This changes result sets silently. Choose a `_bin`/`_cs`
  collation where case-sensitive matching is contractual.
- **`LENGTH` counts bytes** in MySQL and characters in Oracle. Use `CHAR_LENGTH`.
- **Sort order and NULL placement.** MySQL sorts NULLs first ascending; Oracle sorts them last.
  Add explicit ordering where it matters (`ORDER BY x IS NULL, x`).
- **`COUNT(*)` is BIGINT** — widen the receiving type.
- **`GROUP BY` strictness.** If `ONLY_FULL_GROUP_BY` is enabled (the 8.0 default), queries Oracle
  accepted may now be rejected — that is a compile-time failure, but the *fix* (adding columns or
  `ANY_VALUE`) can change results.

---

## 3. Full-text search

| Oracle (app code) | MySQL |
|---|---|
| `CONTAINS(col, :terms) > 0` | `MATCH(col) AGAINST(:terms IN NATURAL LANGUAGE MODE)` |
| `CONTAINS(col, :terms, 1) > 0` … `ORDER BY SCORE(1) DESC` | `MATCH(col) AGAINST(:terms …)` … `ORDER BY MATCH(col) AGAINST(:terms …) DESC` |
| boolean operators (`AND`, `NEAR`, `word*`) | `IN BOOLEAN MODE` with `+`, `-`, `*` |

Flag, don't assume:

- A `FULLTEXT` index must exist on the column, and `MATCH` **must list exactly the indexed
  columns** or MySQL raises "can't find FULLTEXT index matching the column list".
- **Minimum word length and stopwords.** InnoDB's `innodb_ft_min_token_size` defaults to **3**, so
  two-letter terms return nothing. Oracle Text behaves differently. This silently changes results
  for short search terms.
- **Relevance scores are not comparable** to Oracle `SCORE(n)`; ordering is usually similar,
  absolute values are not. Any UI showing a score needs review.
- `NATURAL LANGUAGE MODE` ignores boolean syntax a user types; `BOOLEAN MODE` honours `+/-` but
  applies no relevance ranking by default. Pick deliberately based on the search UX.

---

## 4. Stored-routine call sites

- **Flattened names**: `PKG.PROC(...)` → `<pkg>_<subprogram>(...)`. Take the actual names from the
  migration's conversion log.
- **Function → procedure is a contract change.** A MySQL FUNCTION returns only a scalar, so any
  Oracle function returning a collection/ref cursor became a PROCEDURE. Call sites move from
  `SELECT f(...)` to `CALL p(...)` plus result-set consumption. JDBC `{ call p(?) }` works.
- **No parameter defaults.** MySQL routine parameters cannot have defaults, so callers that relied
  on an Oracle default must now pass every argument.
- **Transaction ownership** where an internal `COMMIT` was removed — confirm `@Transactional`.

---

## 5. ORM / framework specifics

- **Dialect** → `org.hibernate.dialect.MySQLDialect`. Hibernate 6 auto-detects; removing the
  property is often better than swapping it.
- **Schema = database.** An Oracle schema becomes a MySQL database, so `@Table(schema="DEMO")`
  becomes `@Table(catalog="demo")` (or the database moves into the JDBC URL). Getting this wrong
  produces "table doesn't exist" at startup.
- **`@GeneratedValue`** → `GenerationType.IDENTITY` for `AUTO_INCREMENT`. A
  `@SequenceGenerator` has no target and must be replaced.
- **`ddl-auto`** — keep `validate`/`none`; never let Hibernate alter a freshly-migrated schema.
- **`serverTimezone`** — set it explicitly in the URL, or timestamps shift.
- **Identifier case** — decide once (lower case) and be consistent, because
  `lower_case_table_names` and the host filesystem both affect resolution.

---

## 6. Not converted by this module

In-database stored routines and schema DDL (construction phase), and Oracle-specific DBA scripts
shipped with the app (flag them).
