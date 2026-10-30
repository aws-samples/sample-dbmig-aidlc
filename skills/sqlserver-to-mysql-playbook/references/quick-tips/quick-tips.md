# Migration Quick Tips — SQL Server → Aurora MySQL

> Source: AWS Microsoft SQL Server to Amazon Aurora MySQL Migration Playbook — Migration quick tips
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tips.html

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected eight wrong tips (histograms, CHECK enforced, AUTO_INCREMENT persisted, '+' returns 0 silently, DEFAULT keyword works, identifier case, user variables, no DATEADD — all verified) and added an Aurora MySQL 8.4 / 3 section.

These tips can save time as you transition from SQL Server to Aurora MySQL. They address
many of the challenges faced by administrators new to Aurora MySQL, and highlight functional
differences between similar SQL Server and Aurora MySQL features.

## Management

- The concept of a *database* in MySQL isn't the same as in SQL Server. A database in MySQL
  is synonymous with *schema*.
- *(corrected)* There are no statistics objects, but MySQL 8 has column **histograms**
  (`ANALYZE TABLE t UPDATE HISTOGRAM ON col`, verified) in addition to index statistics; they are
  refreshed only manually.
- The equivalent of `CREATE DATABASE… AS SNAPSHOT OF…` in SQL Server resembles Aurora MySQL
  database cloning. However, unlike SQL Server snapshots (which are read-only), Aurora MySQL
  cloned databases are updatable.
- In Aurora MySQL, a *database snapshot* is equivalent to `BACKUP DATABASE… WITH COPY_ONLY`
  in SQL Server.
- Partitioning in Aurora MySQL supports more partition types than SQL Server. However,
  partitioning in Aurora MySQL restricts the use of many other fundamental features such as
  foreign keys.
- Partition `SWITCH` in SQL Server can be performed between any two partitions of any two
  tables. In Aurora MySQL, you can only `EXCHANGE` a table partition with a full table.
- Index statistics hold selectivity only; value distribution comes from histograms where you create
  them. MySQL optimizes each execution, so there is no parameter-sniffing plan cache to manage.

## SQL / T-SQL

- Triggers work differently in Aurora MySQL. You can run triggers for each row. The syntax for
  inserted and deleted for each row is `new` and `old`. They always contain 0 or 1 row.
- You can't modify triggers in Aurora MySQL using the `ALTER` command. Drop and replace a
  trigger instead.
- Aurora MySQL doesn't support the `@@FETCH_STATUS` system parameter for cursors. When you
  declare cursors in Aurora MySQL, create an explicit `HANDLER` object, which can set a
  variable based on the **row not found in cursor** event.
- To run a stored procedure, use `CALL` instead of `EXECUTE`.
- To run a string as a query, use Aurora MySQL prepared statements instead of `sp_executesql`
  or `EXECUTE (<String>)`.
- Aurora MySQL supports `AFTER` and `BEFORE` triggers. There is no equivalent to `INSTEAD OF`
  triggers. The only difference between `BEFORE` and `INSTEAD OF` triggers is that DML
  statements are applied row by row to the base table when using `BEFORE` and don't require an
  explicit action in the trigger. To make changes to data affected by a trigger, you can
  `UPDATE` the new and old tables; the changes are persisted.
- Aurora MySQL doesn't support user defined types. Use base types instead and add column
  constraints as needed.
- The `CASE` keyword in Aurora MySQL isn't only a conditional expression as in SQL Server.
  Depending on context, you can use `CASE` for flow control similar to
  `IF <condition> BEGIN <statement block> END ELSE BEGIN <statement block> END`.
- In Aurora MySQL, terminate `IF` blocks with `END IF`. Also terminate `WHILE` loops with
  `END WHILE`. The same rule applies to `REPEAT` — `END REPEAT` and `LOOP` — `END LOOP`.
- You can't deallocate cursors in Aurora MySQL. Closing them provides the same behavior.
- Aurora MySQL syntax for opening a transaction is `START TRANSACTION` as opposed to
  `BEGIN TRANSACTION`. `COMMIT` and `ROLLBACK` are used without the `TRANSACTION` keyword.
- The default isolation level in Aurora MySQL is `REPEATABLE READ` as opposed to
  `READ COMMITTED` in SQL Server. By default, it also uses consistent reads similar to
  `READ COMMITTED SNAPSHOT` in SQL Server.
- Aurora MySQL supports Boolean expressions in `SELECT` lists using the `=` operator. In
  SQL Server, `=` operators in select lists assign aliases. `SELECT Col1 = 1 FROM T` in
  Aurora MySQL returns a column with the alias `Col1 = 1`, with the value 1 for rows where
  `Col1 = 1`, and 0 for rows where `Col1 <> 1 OR Col1 IS NULL`.
- Aurora MySQL doesn't use special data types for UNICODE data. All string types may use any
  character set and any relevant collation, including types not supported by SQL Server such
  as UTF-8, UTF-32, and so on. A `VARCHAR` column can be of a UTF-8 character set and have a
  `latin1_CI` collation, for example. Similarly, there is no `N` prefix for string literals.
- You can define collations at the server, database, and column level similar to SQL Server.
  You can also define collations at the table level.
- In SQL Server, you can use the `DELETE <Table Name>` syntax omitting the `FROM` keyword.
  This syntax isn't valid in Aurora MySQL. Add the `FROM` keyword to all delete statements.
- `UPDATE` expressions in Aurora MySQL are evaluated in order from left to right. This is
  different from SQL Server and the ANSI standard, which require an all-at-once evaluation.
  For example, in `UPDATE Table SET Col1 = Col1 + 1, Col2 = Col1`, `Col2` is set to the new
  value of `Col1`. The end result is `Col1 = Col2`.
- In Aurora MySQL, you can use multiple rows with `NULL` for a UNIQUE constraint. In SQL
  Server, you can use only one row. Aurora MySQL follows the ANSI standard behavior.
- *(corrected)* `CHECK` constraints are **enforced** on Aurora MySQL 3 / 8.4 (MySQL 8.0.16+, error
  3819, verified); `NOT ENFORCED` replaces `WITH NOCHECK`.
- The Aurora MySQL `AUTO_INCREMENT` column property is similar to `IDENTITY` in SQL Server.
  However, there is a major difference in how sequences are maintained. SQL Server caches a
  set of values in memory and records the last allocation on disk; when the service restarts,
  some values may be lost but the sequence continues from where it left off. In Aurora MySQL,
  each time you restart the service, the seed value for `AUTO_INCREMENT` is reset to one
  increment interval larger than the largest existing value. *(corrected)* That was MySQL 5.7;
  since MySQL 8.0 the counter is **persisted** and survives restarts, as in SQL Server.
- Parameter names in Aurora MySQL don't require a preceding "@". You can declare local
  variables such as `DECLARE MyParam1 INTEGER`.
- Parameters that use the @ sign don't have to be declared first. You can assign a value
  directly, which implicitly declares the parameter. For example, `SET @MyParam = 'A'`.
- The local parameter scope isn't limited to a run scope. You can define or set a parameter in
  one statement, run it, and then query it in the following batch.
- Error handling in Aurora MySQL is called *condition handling*. It uses explicitly created
  objects, named conditions, and handlers. Instead of `THROW` and `RAISERROR`, it uses the
  `SIGNAL` and `RESIGNAL` statements.
- Aurora MySQL doesn't support the `MERGE` statement. Use the `REPLACE` statement and the
  `INSERT… ON DUPLICATE KEY UPDATE` statement as alternatives.
- In Aurora MySQL, you can't concatenate strings with the `+` operator. *(corrected)* `'A' + 'B'`
  **is** valid — it is numeric addition and silently returns `0` (`'abc' + 1` = 1), with only a
  warning (verified). Every string `+` must become `CONCAT('A', 'B')`.
- Aurora MySQL doesn't support aliasing in the select list using `'String Alias' = Expression`.
  Aurora MySQL treats it as a logical predicate, returns 0 or FALSE, and aliases the column
  with the full expression. Use the `AS` syntax instead. (Note this syntax has been deprecated
  as of SQL Server 2008 R2.)
- *(corrected)* `VALUES (DEFAULT, DEFAULT)` and `INSERT INTO t () VALUES ()` work in Aurora MySQL;
  only SQL Server's `INSERT INTO t DEFAULT VALUES` form is a syntax error (all verified).
- **Table and database** names are case-sensitive by default in Aurora MySQL
  (`lower_case_table_names` = 0, settable only at cluster creation; `lab.Ut` vs `lab.ut` → error
  1146, verified); column and routine names are not. If you get an "Object not found" error,
  verify the object name case.
- `DECLARE` local variables exist only within stored routines; scripts use **user variables**
  (`SET @x = …`) instead (see above).
- Aurora MySQL is much stricter than SQL Server about statement terminators. Always use a
  semicolon at the end of statements.
- The syntax for `CREATE PROCEDURE` requires parentheses after the procedure name, similar to
  user-defined functions in SQL Server. You can't use the `AS` keyword before the procedure
  body.
- Beware of control characters when copying and pasting a script into Aurora MySQL clients.
  Aurora MySQL is much more sensitive to these than SQL Server, and they result in frustrating
  syntax errors that are hard to spot.

### String functions

Aurora MySQL has a large set of string functions, more diverse than SQL Server. Some of the
more useful ones:

- `TRIM` isn't limited to full trim or spaces. The syntax is
  `TRIM([{BOTH | LEADING | TRAILING} [<remove string>] FROM] <source string>)`.
- `LENGTH` in MySQL is equivalent to `DATALENGTH` in T-SQL. `CHAR_LENGTH` is the equivalent of
  `LENGTH` in T-SQL.
- `SUBSTRING_INDEX` returns a substring from a string before the specified number of
  occurrences of the delimiter.
- `FIELD` returns the index position of the first argument in the subsequent arguments.
- `FIND_IN_SET` returns the index position of the first argument within the second argument.
- `REGEXP` and `RLIKE` provide support for regular expressions.
- `STRCMP` provides string comparison.

### Date and time functions

Aurora MySQL date and time functions differ from SQL Server functions and can cause confusion
during migration:

- *(corrected)* There is **no `DATEADD`** function (error 1305, verified); use `DATE_ADD(d, INTERVAL n unit)`,
  `TIMESTAMPADD(unit, n, d)` or `DATE_SUB`. `DATEDIFF` exists but returns days only, as `a − b`;
  SQL Server `DATEDIFF` counts boundaries while `TIMESTAMPDIFF` counts complete units — see
  `../tsql/datetime.md`.
- Do not use `CAST` and `CONVERT` for date formatting styles. In Aurora MySQL, use
  `DATE_FORMAT` and `TIME_FORMAT`.
- If your application uses the `ANSI CURRENT_TIMESTAMP` syntax, conversion isn't required. Use
  `NOW` in place of `GETDATE`.

## Aurora MySQL 8.4 / 3 additions (verified 2026-10-29)

- Target **Aurora MySQL 8.4** for new migrations (standard support to April 2032; Aurora MySQL 3 / MySQL 8.0
  to 30 April 2028). Details and the 8.4-vs-3 differences: `../../../oracle-to-mysql-playbook/references/target-baseline-aurora-mysql.md`.
- Aurora's default `sql_mode` is **empty** (default parameter groups, verified 2026-10-30): long values are truncated, invalid dates become `0000-00-00`, NULLs in multi-row inserts become 0, `1/0` returns NULL, `GROUP BY` is not strict,
  zero dates are accepted. Set a stricter `sql_mode` before equivalence testing.
- Native now (5.7 gaps in the original playbook): CTEs, window functions, `CHECK`, `LATERAL` (for `APPLY`),
  `JSON_TABLE` (for `OPENJSON`/`STRING_SPLIT`), `GROUP_CONCAT` (for `STRING_AGG`), `REGEXP_*`, roles,
  `SKIP LOCKED`/`NOWAIT`, `GROUPING()` with `WITH ROLLUP`, functional and invisible indexes.
- Still missing: `MERGE`, sequences, `PIVOT`, `FULL OUTER JOIN`, `GROUPING SETS`, `OUTPUT`, `TOP … WITH TIES`
  (use `RANK()`), `INSTEAD OF` and statement-level triggers, table-valued functions and parameters (use JSON),
  parameter defaults, overloading, filtered and `INCLUDE` indexes, `DEFAULT VALUES`.
- Silent traps (verified): `ON DELETE SET DEFAULT` acts as `RESTRICT`; column-level `REFERENCES` creates no
  FK; `ENGINE=FEDERATED` becomes InnoDB; `#temp` tables can't be referenced twice in one statement (1137);
  unique keys allow many NULLs; the default collation is accent-insensitive and NO PAD.
- 8.4 only: TLS required by default, `caching_sha2_password` for new users, `MASTER`/`SLAVE` statements removed,
  FKs must reference a unique key, no `AUTO_INCREMENT` on `FLOAT`/`DOUBLE`.
- Performance Insights reached end of life (2026-07-31) — use CloudWatch Database Insights and turn on
  `performance_schema` (off by default).

## Conversion notes

For detailed, object-level conversion guidance see the related reference directories:

- T-SQL stored procedures, triggers, cursors, error/condition handling, and other procedural
  constructs: [`../tsql/`](../tsql/)
- ANSI SQL constructs, data types, constraints, and standard query syntax differences:
  [`../ansi-sql/`](../ansi-sql/)
