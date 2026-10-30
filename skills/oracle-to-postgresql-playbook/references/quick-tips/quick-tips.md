# Migration Quick Tips — Oracle → Aurora PostgreSQL

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook — Migration quick tips
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tips.html

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): rewrote outdated tips (MERGE, procedures, partitioning, statistics, virtual columns, GTT behavior, dynamic SQL) for PG 15–18; all marked items verified.

A fast-reference list of functional differences administrators and developers new to
PostgreSQL/Aurora commonly hit. Use as a pre-conversion checklist.

## Management
- *Database Snapshot* (Aurora) ≈ Oracle RMAN backup.
- Partitioning is **declarative** (`PARTITION BY RANGE|LIST|HASH`) since PG 10; the old `INHERITS` + trigger approach is obsolete. No interval partitioning, and no `SPLIT`/`MERGE PARTITION` in PG 18 (verified). Use `pg_partman` 5.4 for automatic partition creation.
- PostgreSQL statistics include per-column most-common values and histograms, plus optional
  multi-column extended statistics (`CREATE STATISTICS`). Prepared statements switch to a
  generic plan after 5 executions (`plan_cache_mode`), similar to Oracle bind peeking issues.
- Missing features (e.g. sending email) are often replaced by AWS services (Lambda, SES).
- Parameters and backups are managed by Amazon RDS (parameter groups, default comparison).
- High availability via read replicas in a few clicks.
- Database links: `dblink` extension (Oracle-like) or `postgres_fdw` (Foreign Data Wrapper); `oracle_fdw` 1.2 is available on Aurora 18 to read from Oracle directly.

## SQL & PL/pgSQL
- Triggers use `NEW` and `OLD` for inserted/deleted row values.
- Cursor status: use `FOUND` / `GET DIAGNOSTICS` instead of `%FOUND`/`%NOTFOUND`/`%ROWCOUNT`.
- Call a procedure with `CALL proc(...)` (PG 11+, `OUT` parameters PG 14+); call a function with
  `SELECT fn(...)` or `PERFORM fn(...)` inside PL/pgSQL.
- Dynamic SQL: Oracle `EXECUTE IMMEDIATE '<string>' USING …` → PL/pgSQL
  `EXECUTE '<string>' USING …` (use `format()` with `%I`/`%L` for identifiers/literals).
- Terminate `IF` blocks with `END IF`; `WHILE..LOOP` with `END LOOP`.
- **Autocommit is ON** by default in drivers and `psql` (as in most Oracle clients except
  SQL*Plus scripts). Make transaction boundaries explicit in the application.
- No special UNICODE data types; any string type can use any charset/collation.
- Collations can be set at server/database/column level, **not** table level.
- `DELETE <table>` without `FROM` is invalid — always include `FROM`.
- Oracle `IDENTITY` → `GENERATED { ALWAYS | BY DEFAULT } AS IDENTITY` (prefer over `SERIAL`).
- Error handling: `EXCEPTION WHEN … THEN` blocks with `SQLSTATE` codes; `GET STACKED
  DIAGNOSTICS` replaces `DBMS_UTILITY.FORMAT_ERROR_BACKTRACE`. An exception block opens a
  subtransaction, so avoid them in tight loops.
- Native **`MERGE` is supported** (PG 15+). PG 17+ adds `RETURNING` with `merge_action()` and
  `WHEN NOT MATCHED BY SOURCE` (verified on 18.6). Convert Oracle `MERGE` directly; use
  `INSERT … ON CONFLICT` only for simple single-row upserts that need its concurrency
  guarantees.
- String concatenation with `||` works as in Oracle.
- PostgreSQL is **strict about semicolons** — terminate every statement.
- Convert Oracle procedures to `CREATE PROCEDURE` (PG 11+), which can `COMMIT`/`ROLLBACK`
  and (PG 14+) return `OUT` parameters through `CALL` (verified on 18.6). Use
  `CREATE FUNCTION` for Oracle functions.
- `GREATEST` and `LEAST` ignore NULLs in PostgreSQL but return NULL in Oracle if any
  argument is NULL. Wrap with a NULL check where it matters.
- `SAVEPOINT` / `ROLLBACK TO SAVEPOINT` are not supported inside functions.
- `BFILE`, `ROWID`, `UROWID` are unsupported — redesign with other types (`ctid` is not a
  stable row id; use the primary key).
- Temporary tables are session-scoped and visible only to the creating session.
  `CREATE GLOBAL TEMPORARY TABLE` is **accepted but `GLOBAL` is ignored** (verified on 18.6),
  so a converted GTT silently becomes a per-session table that must exist in each session.
- Oracle virtual columns → `GENERATED ALWAYS AS (expr)` columns. PG 18 defaults to
  **`VIRTUAL`** (computed on read), but virtual generated columns **cannot be indexed**
  (verified); use `STORED` when the column must be indexed or constrained.
- Unused columns: `ALTER TABLE … DROP COLUMN` is a metadata-only operation (instant).
- No automatic/incremental materialized-view `REFRESH` — use `REFRESH MATERIALIZED VIEW
  CONCURRENTLY` on a schedule (`pg_cron`) or trigger-maintained summary tables.
- Oracle-compatibility helpers on Aurora 18: `orafce` 4.16 (`DUAL`, `NVL`, `DECODE`,
  `ADD_MONTHS`, `DBMS_OUTPUT`, `UTL_FILE`-style functions), and core PG 15+
  `regexp_like`/`regexp_count`/`regexp_instr`/`regexp_substr` (verified). orafce puts most
  objects in the **`oracle` schema** (`oracle.dual`, `oracle.nvl`, `oracle.decode`,
  `oracle.add_months`) plus package-like schemas (`dbms_output`, `dbms_sql`, `dbms_pipe`,
  `dbms_alert`, `dbms_assert`, `dbms_utility`, `dbms_random`, `utl_file`). Either qualify
  calls or add `oracle` to `search_path` (`ALTER ROLE app SET search_path = app, oracle, public`).
  Prefer native PostgreSQL (`COALESCE`, `CASE`, `+ interval`) in converted code and keep
  orafce for hard cases, so the schema does not depend on an extension.
- `''` (empty string) is **not NULL** in PostgreSQL. Oracle treats it as NULL; review
  `= ''`, `IS NULL`, `NVL` and concatenation logic.
- Multiple databases per instance — useful for consolidation projects.
- Beware control characters when pasting scripts — PostgreSQL is far more sensitive than
  Oracle and produces hard-to-find syntax errors.

## Conversion notes
These tips overlap with the detailed `sql-plsql/`, `tables-indexes/`, and `special-features/`
references — treat this page as the index of "gotchas" and follow the per-topic file for the
actual conversion pattern and examples.
