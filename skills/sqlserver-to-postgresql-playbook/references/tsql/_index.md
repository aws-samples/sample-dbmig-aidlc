# T-SQL Conversion References — SQL Server → Aurora PostgreSQL

Distilled from the AWS *SQL Server to Aurora PostgreSQL Migration Playbook* (T-SQL chapter). Each file follows: Conversion category, SCT automation, SQL Server, PostgreSQL, Conversion notes.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29). The playbook targeted PostgreSQL 10–13; several of its workarounds are obsolete. PG 18 defaults used by this toolkit: T-SQL procedures → `CREATE PROCEDURE` (result-set procedures → `RETURNS TABLE` functions), native `MERGE`, `FETCH … WITH TIES`, identity columns (not `SERIAL`), `uuidv7()` for `NEWSEQUENTIALID`, SQL/JSON `JSON_VALUE`/`JSON_QUERY`/`JSON_TABLE`, `string_to_table` for `STRING_SPLIT`, statement-level triggers with transition tables named `inserted`/`deleted`, `EXECUTE FUNCTION`. Cross-engine PG 18 baseline: `../../../oracle-to-postgresql-playbook/references/target-baseline-aurora-postgresql-18.md`.

- **service-broker.md** — No equivalent; re-architect with Amazon SQS + Lambda, or an in-database queue table with `FOR UPDATE SKIP LOCKED` + `pg_notify`; `aws_lambda` extension; `pgmq` not available. [Manual]
- **cast-and-convert.md** — `CAST` is compatible; `CONVERT` styles → `to_char`/`to_date` (style table); `TRY_CAST`/`TRY_CONVERT` → `pg_input_is_valid` (PG 16); `::` operator available. [Assisted]
- **common-language-runtime.md** — .NET CLR unsupported; rewrite in PL/pgSQL, PL/Perl or PL/v8 (`pg_tle` for packaging); external calls via `aws_lambda`; PL/Python/PL/Java not available. [Manual]
- **collations.md** — CI/AI collations → ICU nondeterministic collations (PG 18 supports `LIKE` on them) or `citext`; UTF-8 only (no UTF-16); changing encoding needs dump/restore. [Assisted]
- **cursors.md** — Most cursor ops map directly; PostgreSQL cursors are insensitive (static); `@@FETCH_STATUS`→`FOUND`; `DEALLOCATE` not needed; prefer set-based or `FOR … IN query LOOP`. [Assisted]
- **date-time-functions.md** — Rename functions (`DATEADD`→`+ interval`/`date_add`, `DATEDIFF`→boundary-correct formulas, `EOMONTH`, `ISDATE`→`pg_input_is_valid`); Aurora runs in UTC. [Automatic]
- **string-functions.md** — Mostly compatible; `LEN`→`length(rtrim())`, `REPLICATE`→`repeat`, `STRING_SPLIT`→`string_to_table`, `CHARINDEX`→`strpos`; verified `PATINDEX` UDF (original was wrong for anchored patterns). [Automatic]
- **databases-and-schemas.md** — Each source database → a schema in one target database (no cross-database queries); `dbo` via `search_path`; no `USE`; no filegroups. [Automatic]
- **dynamic-sql.md** — No `sp_executesql`; `EXECUTE format(…%I/%L…) USING …`; never `%s` for identifiers/literals; `INTO` for OUTPUT params; DDL is transactional. [Manual]
- **transactions.md** — Same ANSI levels; `SNAPSHOT`→`REPEATABLE READ`; nested transactions unsupported; `BEGIN TRAN`→`BEGIN`; no server `SET AUTOCOMMIT`; no `COMMIT` in functions or `SAVEPOINT` in PL/pgSQL; COMMIT-in-EXCEPTION hazard. [Assisted]
- **synonyms.md** — No synonyms; emulate with `security_invoker` views (tables; `SELECT *` freezes columns), domains (types), wrapper functions, or `search_path`. [Manual]
- **delete-update-from.md** — `UPDATE … FROM` and `DELETE … USING` are supported (target table not repeated in `FROM`); `RETURNING old/new` (PG 18) replaces `OUTPUT`. [Assisted]
- **stored-procedures.md** — `CREATE PROCEDURE` (`CALL`, `INOUT`/`OUT`) by default; result-set procedures → `RETURNS TABLE` functions; multiple result sets → refcursors; TVPs → composite arrays/`jsonb`; `EXECUTE AS`→`SECURITY DEFINER` + `SET search_path`. [Assisted]
- **error-handling.md** — `TRY…CATCH`→`BEGIN…EXCEPTION`; `THROW`→`RAISE … USING ERRCODE` (safe custom SQLSTATEs); `ERROR_*`→`GET STACKED DIAGNOSTICS`; an EXCEPTION block rolls back the whole block, not only the failing statement. [Manual]
- **flow-control.md** — Mostly maps; no `GOTO`; `BREAK`→`EXIT`, `CONTINUE`→`CONTINUE` (not MySQL `ITERATE`); `WAITFOR DELAY`→`pg_sleep`, `WAITFOR TIME`→`pg_sleep_until`; `PRINT`→`RAISE NOTICE '%'`. [Assisted]
- **full-text-search.md** — Full rewrite to a STORED generated `tsvector` + GIN index and `@@`/`websearch_to_tsquery`; trigram indexes do not serve `@@`; OpenSearch for complex needs. [Manual]
- **graph-features.md** — No native graph (Apache AGE not available); node/edge tables + recursive CTEs with `SEARCH`/`CYCLE`, `pgrouting`, or Amazon Neptune. [Manual]
- **json-and-xml.md** — `JSONB`; SQL/JSON `IS JSON`/`JSON_VALUE`/`JSON_QUERY`/`JSON_TABLE` (PG 16/17) map T-SQL directly; `JSON_MODIFY`→`jsonb_set`; `FOR XML`→`xmlagg`/`xmlelement`; `XMLTABLE` needs prefixed namespaces. [Automatic]
- **merge.md** — Native `MERGE` incl. `WHEN NOT MATCHED BY SOURCE` and `RETURNING merge_action()`/`old`/`new`; `INSERT … ON CONFLICT` for concurrent upserts. [Assisted]
- **pivot-unpivot.md** — No PIVOT/UNPIVOT; `agg(…) FILTER (WHERE …)` for pivot, `CROSS JOIN LATERAL (VALUES …)` + `IS NOT NULL` for unpivot; `crosstab` returns NULL not 0. [Assisted]
- **triggers.md** — Trigger function + `EXECUTE FUNCTION`; `INSERTED`/`DELETED`→statement-level transition tables (one event per trigger) or `NEW`/`OLD`; `INSTEAD OF` on tables→`BEFORE` row trigger returning `NULL`; DDL/logon→event triggers. [Assisted]
- **top-fetch.md** — `TOP (n)`→`LIMIT`/`FETCH FIRST`; `OFFSET…FETCH` unchanged; `WITH TIES` native (PG 13); `PERCENT` needs a `ceil` workaround; no `UPDATE/DELETE TOP`. [Automatic]
- **user-defined-functions.md** — All UDF types → `CREATE FUNCTION`; inline TVFs as `LANGUAGE sql` (inlined by the planner), scalar UDFs with SQL-standard `RETURN` bodies; `APPLY`→`LATERAL`; volatility labels. [Assisted]
- **user-defined-types.md** — Alias UDT→`CREATE DOMAIN`; table types→composite arrays; CLR types→`ltree`/PostGIS; adds enum/range/array. [Automatic]
- **identity-and-sequences.md** — `IDENTITY`→`GENERATED … AS IDENTITY` (not `SERIAL`); `IDENTITY_INSERT`→`OVERRIDING SYSTEM VALUE`; `NEWSEQUENTIALID`→`uuidv7()`; reseed via `RESTART WITH`/`setval`; `SCOPE_IDENTITY`→`RETURNING`. [Assisted]
