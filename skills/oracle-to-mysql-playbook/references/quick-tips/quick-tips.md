# Migration Quick Tips — Oracle → Aurora MySQL

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tips.html

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected four wrong tips (table-level collations, virtual columns, histograms, virtual-column partitioning); verified ||, DELETE, isolation and autocommit notes; added an Aurora MySQL 8.4 / 3 section.

## Management
- A *database snapshot* in Aurora MySQL is the equivalent of an RMAN backup in Oracle.
- Aurora MySQL partitioning lacks Partition Advisor, Preference, Interval, Reference and Automatic List partitioning and global indexes. *(corrected)* Partitioning on a generated (virtual-column-style) column works. Partitioned tables cannot have foreign keys (error 1506) and every unique key must include the partition columns (error 1503) — both verified.
- *(corrected)* MySQL 8 has column **histograms** (`ANALYZE TABLE … UPDATE HISTOGRAM`), but they are refreshed only manually; on Aurora MySQL 8.4.7+ `AUTO UPDATE` is ignored (verified).
- Use Amazon services (e.g. Lambda) to replicate functionality not provided by MySQL, such as sending email.
- Amazon RDS manages parameters and backups; it is useful for checking a parameter's value against its default and comparing across parameter groups.
- You can create replicas with just a few clicks to implement high availability.
- Aurora MySQL has no equivalent to database links — it can only query across databases within the same instance.

## SQL & stored programs
- No support for statement-level triggers or triggers on system events.
- Limited cursor status checks — when declaring cursors, create an explicit `HANDLER` object.
- Use `CALL` (not `EXECUTE`) to run a stored procedure; call functions inside SQL (`SELECT f(x)`).
- To run a string as a query, use Aurora MySQL Prepared Statements instead of `EXECUTE(<String>)`.
- Terminate `IF` blocks with `END IF`, and `WHILE..LOOP` loops with `END LOOP`.
- Auto-commit defaults to `ON` on the server (unlike Oracle) — set it to `OFF` for Oracle-like behavior. Some drivers (PyMySQL, used by this toolkit) default to OFF; JDBC defaults to ON.
- Default isolation is `REPEATABLE READ` (Oracle behaves like `READ COMMITTED`), with gap locks; set `transaction_isolation` in the parameter group if the application assumes Oracle semantics (verified default on 3.13 and 8.4).
- *(corrected)* Collations can be defined at the server, database, **table** and column level (verified: `CREATE TABLE … COLLATE utf8mb4_0900_as_cs`). The default `utf8mb4_0900_ai_ci` is **case- and accent-insensitive** and treats trailing spaces as significant — Oracle comparisons are case-sensitive.
- The `DELETE <Table Name>` syntax that omits `FROM` (valid in Oracle) is invalid (syntax error, verified) — add `FROM` to all `DELETE` statements.
- The `AUTO_INCREMENT` column property is the analog of Oracle `IDENTITY`.
- Error handling is less feature-rich than Oracle — for special needs, log or alert by inserting into tables or catching errors.
- No `MERGE` statement — use `INSERT … ON DUPLICATE KEY UPDATE` (row alias form) and multi-table `UPDATE`/`DELETE`; `REPLACE` deletes and re-inserts the row (fires delete triggers, breaks FKs).
- Do not concatenate strings with `||`: without `PIPES_AS_CONCAT` it is a logical OR and `'a' || 'b'` returns `0` silently (verified) — use `CONCAT()`. `CONCAT` returns NULL if any argument is NULL; Oracle `||` treats NULL as `''`. Use `CONCAT_WS('', …)` or `COALESCE` for Oracle semantics.
- Stricter about statement terminators than Oracle — always use semicolons at the end of statements.
- No support for the `BFILE`, `ROWID`, and `UROWID` data types.
- Temporary tables are retained only for the session, and only the creating session can query them.
- *(corrected)* Virtual columns **are** supported: `col … AS (expr) VIRTUAL|STORED` (verified); they can be indexed. `SET UNUSED` → `ALTER TABLE … DROP COLUMN …, ALGORITHM=INSTANT` (verified) or `INVISIBLE` columns.
- No support for materialized views — use views or summary tables instead.
- Explore AWS for features that can be replaced with Amazon services to ease maintenance and reduce cost.
- You can create multiple databases in a single instance — useful for consolidation projects.
- Beware of control characters when copying/pasting scripts into Aurora MySQL clients; it is far more sensitive to them than Oracle and they cause hard-to-find syntax errors.

## Aurora MySQL 8.4 / 3 additions (verified 2026-10-29)
- Target **Aurora MySQL 8.4** for new migrations (standard support to April 2032; Aurora MySQL 3 / MySQL 8.0 to 30 April 2028). Details and version differences: `../target-baseline-aurora-mysql.md`.
- Aurora's default `sql_mode` is **empty** (default parameter groups, verified 2026-10-30): long values are truncated, invalid dates become `0000-00-00`, NULLs in multi-row inserts become 0, `1/0` returns NULL, `GROUP BY` is not strict — all silently. Set a strict `sql_mode` in a custom cluster parameter group before testing equivalence and before cutover; `dbmig` uses a strict mode on its own sessions.
- Native now (were 5.7 gaps in the playbook): CTEs / `WITH RECURSIVE` (for `CONNECT BY`), window functions, `REGEXP_LIKE/INSTR/SUBSTR/REPLACE`, roles, `CHECK` constraints, `JSON_TABLE`, `LATERAL`, `INTERSECT`/`EXCEPT`, `SKIP LOCKED`/`NOWAIT`, functional and descending indexes, instant DDL.
- Still missing: sequences, packages, `MERGE`, `REGEXP_COUNT`, `GROUPING SETS`, `NULLS FIRST`, `RETURNING`, `FETCH FIRST`, autonomous transactions, statement-level / `INSTEAD OF` triggers, parameter defaults and overloading, `%TYPE`/`%ROWTYPE`.
- `LENGTH()` counts bytes — use `CHAR_LENGTH()`. `GROUP_CONCAT` truncates at 1024 bytes by default.
- MySQL `NCHAR`/`NVARCHAR` are `utf8mb3` and reject emoji; map Oracle national types to `utf8mb4` `VARCHAR`.
- Some DDL options are silently ignored: `ENGINE=FEDERATED` becomes InnoDB, `ROW_FORMAT=COMPRESSED` becomes COMPACT.
- 8.4 only: TLS required by default, `caching_sha2_password` for new users, `MASTER`/`SLAVE` statements removed, FKs must reference a unique key, no `AUTO_INCREMENT` on `FLOAT`/`DOUBLE`.
- Performance Insights reached end of life (2026-07-31) — use CloudWatch Database Insights, and turn on `performance_schema` (off by default).

## Conversion notes
- For detailed, object-level conversion guidance see the playbook references under
  `../sql-plsql/` (SQL and PL/SQL constructs: cursors, triggers, error handling, `MERGE`,
  prepared statements, sequences/`AUTO_INCREMENT`, string operators) and
  `../special-features/` (partitioning, materialized views, database links, virtual/unused
  columns, and other Oracle-specific capabilities and their Aurora MySQL workarounds).
