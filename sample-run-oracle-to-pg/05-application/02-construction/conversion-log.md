# App conversion log — JavaBobsUsedBooks

Applied the approved change plan (12 items) to 18 files (+133 / −51; exact changes in `app.diff`).
Backup: `backup/<ts>/` full tree before the first edit (`MANIFEST.md`).

| # | Change | Files | Rule / cite |
|---|---|---|---|
| 1 | Full-text: `CONTAINS/SCORE` → `to_tsvector(...) @@ websearch_to_tsquery(...)` + `ts_rank`, expression identical to `books_text_idx` | `BookRepository` | `fulltext_redesign` decision A; `engines/oracle-to-postgresql/checks/non-portable-constructs.md` |
| 2 | Query builder stops emitting `fuzzy(t, 40) OR …`; terms joined with ` or ` | `BookService` | same (BEHAVIOURAL: no fuzzy matching) |
| 3 | Datasource: PG URL/driver, dialect removed, credentials as `${DB_*}` | `application.properties` | `engines/oracle-to-postgresql/app/app-config.yaml` |
| 4 | `ojdbc17` removed | `pom.xml` | app-config.yaml |
| 5 | 10 × `Boolean` → `@JdbcTypeCode(SMALLINT)`; 5 × `LocalDate` → `@JdbcTypeCode(TIMESTAMP)`; `@Lob byte[]` → `@JdbcTypeCode(VARBINARY)` | 8 entities | `engines/oracle-to-postgresql/app/app-sql-rules.md` §5a (ORM type obligations) |
| 6 | URL parsing after `//`, query string dropped, no raw-URL fallback | `DatabaseInfoConfig`, `DatabaseInfoController` | URL format + credential-leak path |
| 7 | **New in this run:** `LoadCoverImages` resolves `${VAR}` / `${VAR:default}` from the environment | `utils/LoadCoverImages` | change 3 would otherwise pass literal placeholders to `DriverManager` (missed by the previous run) |
| 8 | Demo classes: dialect-only conversion (ROWNUM → LIMIT, NVL, DECODE, TO_DATE, ADD_MONTHS, LISTAGG, MONTHS_BETWEEN) + PRE-EXISTING BROKEN banner | `demo/OracleBookRepository`, `demo/OracleBookService` | like-for-like; source catalog evidence in `inventory.md` |
| 9 | Comment on the `get_customer_history` call (routine absent in the source) | `CustomerRepository` | pre-existing broken |
