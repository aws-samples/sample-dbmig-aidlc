# T-SQL Migration References — SQL Server → Aurora MySQL

Distilled from the AWS *Microsoft SQL Server 2019 to Amazon Aurora MySQL Migration Playbook*, chapter "Migrating T-SQL features". One file per topic.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29). Several of the original "unsupported" items are native on MySQL 8 (CTEs, window functions, `STRING_AGG`→`GROUP_CONCAT`, `STRING_SPLIT`/`OPENJSON`→`JSON_TABLE`, multi-table `UPDATE … JOIN`, `LEAVE`/`ITERATE` for `BREAK`/`CONTINUE`, histograms, persisted `AUTO_INCREMENT`). Baseline: `../../../oracle-to-mysql-playbook/references/target-baseline-aurora-mysql.md`.

- [collations.md](collations.md) — `NCHAR`/`NVARCHAR` → `utf8mb4` `CHAR`/`VARCHAR` (MySQL `NCHAR` is utf8mb3); verified collation map (CI_AS → `utf8mb4_0900_as_ci`); NO PAD vs PAD SPACE trailing spaces. (Assisted)
- [cursors.md](cursors.md) — Static, forward-only, read-only cursors with `NOT FOUND` handlers; `SELECT INTO` no-rows ends cursor loops (verified trap). (Assisted)
- [datetime.md](datetime.md) — `GETDATE`→`NOW`, `DATEADD`→`DATE_ADD`; SQL Server `DATEDIFF` counts boundaries — `TIMESTAMPDIFF` counts complete units (verified), use boundary formulas. (Assisted)
- [string-functions.md](string-functions.md) — `+`→`CONCAT` (`'a'+'b'` = 0), `LEN`→`CHAR_LENGTH(RTRIM())`, `STUFF`→`INSERT`, `STRING_AGG`→`GROUP_CONCAT`, `STRING_SPLIT`→`JSON_TABLE` (verified). (Automatic)
- [databases-schemas.md](databases-schemas.md) — Each SQL Server schema → a MySQL database (toolkit convention); names case-sensitive by default. (Manual)
- [transactions.md](transactions.md) — Default `REPEATABLE READ` (set via `transaction_isolation`); `IMPLICIT_TRANSACTIONS ON`→`autocommit=0`; savepoints; DDL commits implicitly. (Assisted)
- [delete-update.md](delete-update.md) — `UPDATE … FROM`/`DELETE … FROM` → multi-table `UPDATE t JOIN …` / `DELETE t FROM t JOIN …` (verified); left-to-right `SET`. (Automatic)
- [stored-procedures.md](stored-procedures.md) — `CREATE PROCEDURE (…)`; TVPs → JSON + `JSON_TABLE`; no defaults, named calls or overloading; `RETURN` → `OUT`. (Assisted)
- [error-handling.md](error-handling.md) — `TRY/CATCH`→handlers, `THROW`→`SIGNAL … SET MESSAGE_TEXT = var` (variables allowed), `ERROR_*()`→`GET DIAGNOSTICS`. (Assisted)
- [flow-control.md](flow-control.md) — `IF … THEN … END IF`, `WHILE … DO`; `BREAK`/`CONTINUE` → `LEAVE`/`ITERATE label`; `WAITFOR`→`SLEEP`; no `GOTO`. (Automatic)
- [full-text-search.md](full-text-search.md) — `CONTAINS`/`FREETEXT` → `MATCH … AGAINST`; no stemming; `ngram` parser for CJK; OpenSearch for advanced search. (Manual)
- [graph.md](graph.md) — No graph tables; node/edge tables + `WITH RECURSIVE` for multi-hop; Neptune for real graph workloads. (Manual)
- [xml.md](xml.md) — Minimal XML (`ExtractValue`/`UpdateXML`); JSON: `OPENJSON`→`JSON_TABLE`, `FOR JSON`→`JSON_ARRAYAGG`, `ISJSON`→`JSON_VALID`. (Manual)
- [merge.md](merge.md) — No `MERGE`: `INSERT … ON DUPLICATE KEY UPDATE` (row alias) + `DELETE … LEFT JOIN` (verified). (Manual)
- [pivot.md](pivot.md) — No `PIVOT`/`UNPIVOT`: `CASE` aggregation; `LATERAL` UNPIVOT that drops NULLs (verified). (Manual)
- [synonyms.md](synonyms.md) — No synonyms; updatable views, db-qualified names, wrapper routines. (Manual)
- [top-fetch.md](top-fetch.md) — `TOP`/`OFFSET…FETCH` → `LIMIT … OFFSET`; `WITH TIES` → `RANK()`; `PERCENT` → `CEIL` count. (Automatic)
- [triggers.md](triggers.md) — Row triggers only, one event each; `INSERTED`/`DELETED`→`NEW`/`OLD`; no `CREATE OR REPLACE`, `INSTEAD OF`, or DDL triggers. (Manual)
- [udf.md](udf.md) — Scalar functions only; DML allowed, DDL/`COMMIT` rejected; TVFs → views, `LATERAL`, `JSON_TABLE` or procedures. (Manual)
- [udt.md](udt.md) — No UDTs/TVPs; base types + `CHECK`; TVP → JSON parameter + `JSON_TABLE` (verified). (Manual)
- [identity-sequences.md](identity-sequences.md) — `IDENTITY`→`AUTO_INCREMENT` (persisted since 8.0); no sequences (sequence table + `LAST_INSERT_ID(expr)`). (Manual)
- [managing-statistics.md](managing-statistics.md) — Index statistics + column histograms (manual refresh); `ANALYZE TABLE` after loads. (Manual)
