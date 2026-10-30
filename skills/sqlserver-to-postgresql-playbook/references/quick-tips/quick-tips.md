# Migration Quick Tips — SQL Server to Aurora PostgreSQL

> **Source:** Migration quick tips — Microsoft SQL Server 2019 to Amazon Aurora PostgreSQL Migration Playbook
> **URL:** https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tips.html

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): rewrote this checklist. Several original tips were outdated for PG ≥ 11 or described MySQL rather than PostgreSQL (`REPLACE` / `ON DUPLICATE KEY UPDATE`, `SUBSTRING_INDEX`, `FIELD`, "`CAST` is for collations", "no `CREATE PROCEDURE`", "`SERIAL` resets on restart"). Corrected items are marked *(corrected)*; items marked *verified* were run on 18.6.

These tips address common challenges and functional differences encountered when transitioning from Microsoft SQL Server to Amazon Aurora PostgreSQL.

## Management

- SQL Server `CREATE DATABASE … AS SNAPSHOT OF …` resembles an **Aurora fast clone** (copy-on-write, whole cluster). Unlike SQL Server snapshots, which are read-only, clones are updatable.
- In Aurora terminology, a *DB cluster snapshot* is equivalent to SQL Server `BACKUP DATABASE … WITH COPY_ONLY`.
- *(corrected)* Partitioning is **declarative** (`PARTITION BY RANGE|LIST|HASH`); `INHERITS`-based partitioning is legacy. No `RANGE LEFT`, no `SPLIT`/`MERGE`; `SWITCH` → `DETACH`/`ATTACH`. See `../physical-storage/partitioning.md`.
- *(corrected)* PostgreSQL statistics include most-common values and histograms per column, plus optional multi-column statistics (`CREATE STATISTICS`). Prepared statements switch to a generic plan after five executions (`plan_cache_mode`), which is the PostgreSQL form of parameter-sniffing issues.
- Missing features (sending email, file I/O, OS commands) are implemented with AWS services: Lambda (`aws_lambda.invoke`), SES, S3 (`aws_s3`).
- Scheduling: `pg_cron` for in-database jobs, EventBridge Scheduler for external ones (see `../management/sql-server-agent.md`).
- Parameters and backups are managed by Amazon RDS (parameter groups, automated backups, PITR).
- High availability: Aurora Replicas (same Region) and Global Database (cross-Region).
- Linked servers → `postgres_fdw`, `tds_fdw` (to SQL Server), `dblink`.
- **Babelfish** for Aurora PostgreSQL (in Aurora 18.6 as `babelfishpg_tsql` 6.2.0) accepts T-SQL over the TDS protocol. It is an alternative migration path that keeps most application code unchanged. This toolkit converts to native PostgreSQL instead; record which path the customer chose.

## SQL / T-SQL

- Triggers call a trigger **function**. Row-level triggers use `NEW`/`OLD` instead of `inserted`/`deleted`; statement-level triggers can use transition tables (`REFERENCING NEW TABLE AS inserted`), which behave like SQL Server's set-based `inserted`/`deleted` tables.
- *(corrected)* Cursors: replace `@@FETCH_STATUS` with the `FOUND` variable (`EXIT WHEN NOT FOUND`). There is no `HANDLER` object in PL/pgSQL; that is MySQL.
- *(corrected)* Run a **procedure** with `CALL proc(...)` and a **function** with `SELECT fn(...)` (or `PERFORM fn(...)` inside PL/pgSQL). `EXEC proc` → `CALL proc`.
- *(corrected)* Dynamic SQL: `EXECUTE (@sql)` / `sp_executesql` → PL/pgSQL `EXECUTE sql_text USING params` (with `format('%I', …)` for identifiers).
- Terminate `IF` blocks with `END IF` and loops with `END LOOP`; `ELSE IF` → `ELSIF`.
- Transactions: `BEGIN TRANSACTION` / `START TRANSACTION`, `COMMIT`, `ROLLBACK` all work as SQL statements. Inside PL/pgSQL `BEGIN` starts a code block, not a transaction; use `COMMIT`/`ROLLBACK` in procedures. `SAVE TRANSACTION` → an inner `BEGIN … EXCEPTION … END` block (no `SAVEPOINT` in PL/pgSQL).
- Any error aborts the whole transaction (like `XACT_ABORT ON`); the transaction must be rolled back before new statements run.
- No special `UNICODE` types: with a `UTF8` database every string type stores any character. `NVARCHAR(n)` → `varchar(n)`.
- Collations can be defined at the database, column, and expression level (`COLLATE`), but **not** at the table level. Case-insensitive comparison needs a nondeterministic ICU collation (PG 18 supports `LIKE` with it, verified) or `citext`.
- `DELETE <table>` without `FROM` is invalid; always write `DELETE FROM`. `DELETE/UPDATE … FROM` joins become `DELETE … USING` / `UPDATE … FROM` (see `../tsql/delete-update-from.md`).
- *(corrected)* `UNIQUE` allows many NULLs by default; SQL Server allows one. Use `UNIQUE NULLS NOT DISTINCT` (PG 15+, verified) to keep SQL Server behavior.
- *(corrected)* `IDENTITY` → `GENERATED { BY DEFAULT | ALWAYS } AS IDENTITY` (prefer it over `SERIAL`). PostgreSQL sequences **persist** across restarts. Like SQL Server's identity cache, unused cached values can be lost (gaps); they do **not** reset to the table's maximum value. After loading data with explicit values, reset with `ALTER TABLE … ALTER COLUMN … RESTART WITH n` or `./dbmig reset-identity`.
- Variables: declare them in PL/pgSQL (`DECLARE v int;`), no `@` prefix. For session-scoped values (SQL Server `SESSION_CONTEXT`), use custom settings: `SELECT set_config('app.user_id', '42', false);` / `current_setting('app.user_id', true)`.
- Error handling: `BEGIN … EXCEPTION WHEN … THEN … END` with `SQLSTATE` and `GET STACKED DIAGNOSTICS`; `THROW`/`RAISERROR` → `RAISE EXCEPTION … USING ERRCODE`. See `../tsql/error-handling.md`.
- *(corrected)* `MERGE` **is supported** (PG 15+; `RETURNING merge_action()` and `WHEN NOT MATCHED BY SOURCE` in PG 17+, verified). Convert SQL Server `MERGE` directly. `INSERT … ON CONFLICT` is the PostgreSQL upsert for simple cases. `REPLACE` / `ON DUPLICATE KEY UPDATE` are MySQL syntax and do not exist in PostgreSQL.
- *(corrected)* String concatenation: `+` → `||`. Both return NULL if an operand is NULL (`'a' || NULL` is NULL, verified), like SQL Server with `CONCAT_NULL_YIELDS_NULL ON`. `CONCAT(…)` ignores NULLs in both engines.
- Aliasing with `'Alias' = Expression` or `Alias = Expression` in the select list is not supported; PostgreSQL evaluates it as a comparison. Use `Expression AS Alias`.
- *(corrected)* String functions:
  - `LEN(s)` (excludes trailing spaces) → `length(rtrim(s))`; `length()` counts trailing spaces (`length('ab  ') = 4`, verified).
  - `DATALENGTH(s)` → `octet_length(s)` (bytes; `octet_length('é') = 2` in UTF8, verified).
  - `CHARINDEX(sub, s)` → `strpos(s, sub)` / `position(sub IN s)`.
  - `STRING_SPLIT` → `string_to_table(s, ',')` (PG 14+) or `unnest(string_to_array(s, ','))`.
  - `TRIM([chars FROM] s)` works; `LTRIM`/`RTRIM` accept a character set.
  - Regex: `~`, `regexp_like`, `regexp_replace`, `regexp_substr`, `regexp_count` (PG 15+).
  - `SUBSTRING_INDEX` and `FIELD` (listed in the original tips) are **MySQL** functions; they do not exist in PostgreSQL (verified).
- *(corrected)* `CAST(x AS type)` and `x::type` convert data types. PostgreSQL `convert()` is a byte-encoding function, not a type conversion. T-SQL `CONVERT(type, x, style)` → `to_char`/`to_timestamp`/`CAST`. See `../tsql/cast-and-convert.md`.
- PostgreSQL is much stricter than SQL Server about statement terminators: end every statement with a semicolon. There is no `GO` batch separator.
- *(corrected)* `CREATE PROCEDURE` **is supported** (PG 11+), with `COMMIT`/`ROLLBACK` and `INOUT`/`OUT` parameters returned by `CALL` (PG 14+, verified). Procedures that return result sets → `RETURNS TABLE` functions or `INOUT refcursor`. See `../tsql/stored-procedures.md`.
- `TOP n` → `LIMIT n` / `FETCH FIRST n ROWS ONLY`; `TOP n WITH TIES` → `FETCH FIRST n ROWS WITH TIES`.
- `NOLOCK` hints can be dropped: PostgreSQL readers never block writers and never read uncommitted data.
- `GETDATE()` → `LOCALTIMESTAMP` / `now()` (both fixed at transaction start); `SYSDATETIME()` → `clock_timestamp()`.
- Beware of control characters when copying and pasting a script into PostgreSQL clients; PostgreSQL is more sensitive to them than SQL Server, and the resulting syntax errors are hard to find.

## Conversion notes

- For T-SQL procedural conversion details (cursors, triggers, sequences/identity, stored procedures, error handling, transaction control), see `../tsql/`.
- For ANSI-standard SQL conversion details (joins, `GROUP BY`, `UNIQUE`/`NULL` semantics, `MERGE`, string functions), see `../ansi-sql/`.
- PostgreSQL 18 baseline and verified behavior differences: `../target-baseline-aurora-postgresql-18.md`.
