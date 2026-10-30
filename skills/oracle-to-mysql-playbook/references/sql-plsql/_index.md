# SQL and PL/SQL — Oracle → Aurora MySQL Reference Index

Distilled from the AWS Oracle→Aurora MySQL Migration Playbook (SQL and PL/SQL chapter). Each file follows: topic, source/URL, conversion category, SCT automation, Oracle vs MySQL examples, and conversion notes.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29). The playbook targeted Aurora MySQL 5.7; CTEs, window functions, `REGEXP_*` functions and `JSON_TABLE` are native on both current versions. Still missing: `MERGE`, sequences, packages, `REGEXP_COUNT`, `GROUPING SETS`, `NULLS FIRST`, `RETURNING`, parameter defaults, overloading. Baseline and 8.4-vs-3 differences: `../target-baseline-aurora-mysql.md`.

- [single-row-and-aggregate-functions.md](single-row-and-aggregate-functions.md) — Function mappings with verified traps: `LENGTH` counts bytes (`CHAR_LENGTH`), `TRUNCATE(n,0)`, `SUBSTR` position 0, `ADD_MONTHS`/`MONTHS_BETWEEN` month ends, `DECODE` NULLs, `LISTAGG→GROUP_CONCAT` truncation, no `FETCH FIRST`.
- [create-table-as-select.md](create-table-as-select.md) — CTAS works but copies no keys/indexes; `WITH [NO] DATA` is a syntax error; `CREATE TABLE … LIKE`.
- [common-table-expressions.md](common-table-expressions.md) — `WITH [RECURSIVE]` native; `CONNECT BY` → recursive CTE (widen anchor columns, `cte_max_recursion_depth` 1000, no `SEARCH`/`CYCLE`).
- [sequences-and-auto-increment.md](sequences-and-auto-increment.md) — No `CREATE SEQUENCE`; `AUTO_INCREMENT` (persisted since 8.0; integer only on 8.4); verified `LAST_INSERT_ID(expr)` sequence-table pattern.
- [insert-from-select.md](insert-from-select.md) — Compatible except `INSERT ALL/FIRST`, subquery targets and `LOG ERRORS`; `ON DUPLICATE KEY UPDATE` / `INSERT IGNORE` caveats.
- [multi-version-concurrency-control.md](multi-version-concurrency-control.md) — InnoDB MVCC; `LOCK TABLES` commits and is not allowed in procedures; gap locks under `REPEATABLE READ`; `NOWAIT`/`SKIP LOCKED`; deadlock retry (1213).
- [merge-statement.md](merge-statement.md) — No `MERGE`: `INSERT … ON DUPLICATE KEY UPDATE` (row alias) + multi-table `UPDATE`/`DELETE`; verified conversion of the Oracle example.
- [olap-and-window-functions.md](olap-and-window-functions.md) — Window functions native; gaps: `IGNORE NULLS`, `PERCENTILE_*`/`MEDIAN`, `RATIO_TO_REPORT`, `KEEP`, `GROUPING SETS`.
- [transaction-model.md](transaction-model.md) — Default `REPEATABLE READ`; set via `transaction_isolation` cluster parameter; DDL commits; no autonomous transactions; no `COMMIT` in functions/triggers.
- [anonymous-block.md](anonymous-block.md) — Still no anonymous blocks on 3 / 8.4: temporary procedure or a set-based statement.
- [conversion-functions.md](conversion-functions.md) — `TO_CHAR`/`TO_NUMBER` format models → `DATE_FORMAT`/`CAST`/`LPAD`; `FORMAT` adds thousands separators; bad numbers cast to 0, not an error.
- [cursors.md](cursors.md) — Asensitive, read-only, forward-only; parameterized cursors use variables (not `PREPARE`); `SELECT INTO` no-rows ends cursor loops (verified trap).
- [dbms-datapump-and-s3.md](dbms-datapump-and-s3.md) — No `DBMS_DATAPUMP`: S3 integration (CSV only), snapshot export, MySQL Shell dump utilities.
- [dbms-output-and-select.md](dbms-output-and-select.md) — `DBMS_OUTPUT` → `SELECT` result sets (callers must read all); log table or `SIGNAL '01000'` warnings.
- [dbms-random-and-rand.md](dbms-random-and-rand.md) — `DBMS_RANDOM`→`RAND()`; constant seed repeats; `RANDOM_BYTES` for secure values.
- [dbms-redefinition.md](dbms-redefinition.md) — No online redefinition: instant DDL (verified), online DDL, blue/green deployments, gh-ost.
- [dbms-sql.md](dbms-sql.md) — No `DBMS_SQL`: `PREPARE`/`EXECUTE` with the same restrictions as `EXECUTE IMMEDIATE`.
- [execute-immediate-and-prepare.md](execute-immediate-and-prepare.md) — `EXECUTE IMMEDIATE`→`PREPARE`/`EXECUTE`: `USING` takes `@` variables only, `SELECT … INTO @v` for results, one statement, not in functions; backtick-quote identifiers.
- [procedures-and-functions.md](procedures-and-functions.md) — No packages (`<package>_<subprogram>`, 64-char names), no overloading, no parameter defaults, no `%TYPE`; `SIGNAL` for `RAISE_APPLICATION_ERROR`; DEFINER rules.
- [regular-expressions.md](regular-expressions.md) — `REGEXP_LIKE/INSTR/SUBSTR/REPLACE` native (no `REGEXP_COUNT`); case follows collation (add `'c'`), `$1` back-references, no `'x'` flag.
- [timezone-and-convert-tz.md](timezone-and-convert-tz.md) — No tz-aware type; Aurora runs in UTC with named zones pre-loaded; `TIMESTAMP` ends in 2038.
- [user-defined-functions.md](user-defined-functions.md) — Scalar functions only; DML allowed but no DDL/`COMMIT`/dynamic SQL; no UDFs in generated columns or functional indexes.
- [utl-file-and-s3.md](utl-file-and-s3.md) — No `UTL_FILE`: `SELECT INTO OUTFILE S3` / `LOAD DATA FROM S3` with staging tables; roles and parameters verified.
- [utl-mail-smtp-and-sns.md](utl-mail-smtp-and-sns.md) — No in-DB email: SNS event notifications, queue table, or native `lambda_async()` (the `mysql.lambda_async` procedure is gone).
