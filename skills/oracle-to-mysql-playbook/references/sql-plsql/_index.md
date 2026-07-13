# SQL and PL/SQL — Oracle → Aurora MySQL Reference Index

Distilled from the AWS Oracle→Aurora MySQL Migration Playbook (SQL and PL/SQL chapter). Each file follows: topic, source/URL, conversion category, SCT automation, Oracle vs MySQL examples, and conversion notes.

- [single-row-and-aggregate-functions.md](single-row-and-aggregate-functions.md) — Numeric/char/date/null/aggregate function mappings (`TRUNC→TRUNCATE`, `NVL→IFNULL`, `LISTAGG→GROUP_CONCAT`); regex functions need simulation.
- [create-table-as-select.md](create-table-as-select.md) — CTAS is fully compatible; MySQL makes parentheses and `WITH DATA` optional.
- [common-table-expressions.md](common-table-expressions.md) — Aurora MySQL 5.7 has no CTEs: use derived tables (non-recursive) and loops (recursive); MySQL 8 supports them natively.
- [sequences-and-auto-increment.md](sequences-and-auto-increment.md) — No independent SEQUENCE objects; map `IDENTITY`→`AUTO_INCREMENT`; counter not persisted across restart.
- [insert-from-select.md](insert-from-select.md) — Compatible except Oracle `error_logging_clause` and subquery target; use `ON DUPLICATE KEY UPDATE`.
- [multi-version-concurrency-control.md](multi-version-concurrency-control.md) — InnoDB MVCC vs Oracle locks; MySQL auto-commits by default; READ/WRITE table locks; record/gap locks.
- [merge-statement.md](merge-statement.md) — No `MERGE`: use `REPLACE` or `INSERT … ON DUPLICATE KEY UPDATE`, or split into INSERT/UPDATE/DELETE.
- [olap-and-window-functions.md](olap-and-window-functions.md) — Aurora MySQL 5.7 has no window functions: rewrite with correlated subqueries; MySQL 8 supports them.
- [transaction-model.md](transaction-model.md) — Default isolation `REPEATABLE READ` (vs Oracle `READ COMMITTED`); no nested transactions; CHAIN/RELEASE options.
- [anonymous-block.md](anonymous-block.md) — No anonymous blocks: use stored procedures or `START TRANSACTION`.
- [conversion-functions.md](conversion-functions.md) — `TO_CHAR`/`TO_NUMBER` format models map to `DATE_FORMAT`/`FORMAT`/`CAST`/`STR_TO_DATE`.
- [cursors.md](cursors.md) — Cursors only inside routines; read-only, forward-only `FETCH NEXT`; replace `%`-attributes with handlers/counters.
- [dbms-datapump-and-s3.md](dbms-datapump-and-s3.md) — No `DBMS_DATAPUMP`: use `SELECT INTO OUTFILE S3` / `LOAD DATA FROM S3` + metadata tables.
- [dbms-output-and-select.md](dbms-output-and-select.md) — Replace `DBMS_OUTPUT.PUT_LINE` with `SELECT`; output is a result set, not a buffer.
- [dbms-random-and-rand.md](dbms-random-and-rand.md) — `DBMS_RANDOM`→`RAND()` (+`FLOOR`/`MD5`/`SUBSTRING` for ranges/strings); no `NORMAL`.
- [dbms-redefinition.md](dbms-redefinition.md) — No online redefinition: copy via CTAS/mysqldump + trigger-based delta + cutover, or online DDL.
- [dbms-sql.md](dbms-sql.md) — No `DBMS_SQL`: use stored procedures and `PREPARE`/`EXECUTE`.
- [execute-immediate-and-prepare.md](execute-immediate-and-prepare.md) — `EXECUTE IMMEDIATE`→`PREPARE`/`EXECUTE` (`:n`→`?`); no result-returning or anonymous-block execution.
- [procedures-and-functions.md](procedures-and-functions.md) — Map `CREATE PROCEDURE`/`FUNCTION` (drop `AS`, parenthesize params); no packages; convert security context and error raising.
- [regular-expressions.md](regular-expressions.md) — Aurora MySQL 5.7 only has `REGEXP`/`RLIKE`; simulate `REGEXP_*`; escape `\\`; MySQL 8 adds Oracle-style functions.
- [timezone-and-convert-tz.md](timezone-and-convert-tz.md) — No `TIMESTAMP WITH TIME ZONE` column type; use `CONVERT_TZ` at query time.
- [user-defined-functions.md](user-defined-functions.md) — Scalar UDFs only (drop `AS`, explicit `DETERMINISTIC`); no table-valued functions (use views/procedures).
- [utl-file-and-s3.md](utl-file-and-s3.md) — No `UTL_FILE`: use `SELECT INTO OUTFILE S3` / `LOAD DATA FROM S3` (bulk, set-based).
- [utl-mail-smtp-and-sns.md](utl-mail-smtp-and-sns.md) — No in-DB email: use Amazon SNS (RDS event notifications) or a queue table + AWS Lambda integration.
