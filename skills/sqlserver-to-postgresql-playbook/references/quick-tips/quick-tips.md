# Migration Quick Tips — SQL Server to Aurora PostgreSQL

> **Source:** Migration quick tips — Microsoft SQL Server 2019 to Amazon Aurora PostgreSQL Migration Playbook
> **URL:** https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tips.html

These tips address common challenges and functional differences encountered when transitioning from Microsoft SQL Server to Amazon Aurora PostgreSQL.

## Management

- The equivalent of SQL Server's `CREATE DATABASE… AS SNAPSHOT OF…` resembles Aurora PostgreSQL database cloning. However, unlike SQL Server snapshots (which are read-only), Aurora PostgreSQL cloned databases are updatable.
- In Aurora PostgreSQL terminology, *Database Snapshot* is equivalent to SQL Server `BACKUP DATABASE… WITH COPY_ONLY`.
- Partitioning in Aurora PostgreSQL is called `INHERITS` tables and behaves completely differently in terms of management.
- Unlike SQL Server's statistics, Aurora PostgreSQL does not collect detailed key value distribution; it relies on selectivity only. When troubleshooting run issues, be aware that parameter values are insignificant to plan choices.
- Many missing features (such as sending emails) can be achieved with quick implementations of Amazon services such as Lambda.
- Parameters and backups are managed by Amazon RDS. This is very useful for checking a parameter's value against its default and comparing parameter groups.
- High availability can be implemented in a few clicks by creating replicas.
- With Database Links, the `db_link` extension is similar to SQL Server.

## SQL / T-SQL

- Triggers work differently: you can run triggers for each row. The syntax for inserted and deleted for each row is `new` and `old`.
- Aurora PostgreSQL does not support the `@@FETCH_STATUS` system parameter for cursors. When declaring cursors, create an explicit `HANDLER` object.
- To run a stored procedure or function, use `SELECT` instead of `EXECUTE`.
- To run a string as a query, use Aurora PostgreSQL Prepared Statements instead of the `EXECUTE (<String>)` syntax.
- Terminate `IF` blocks with `END IF` and `WHILE..LOOP` loops with `END LOOP`.
- Use `START TRANSACTION` to open a transaction instead of `BEGIN TRANSACTION`. Use `COMMIT` and `ROLLBACK` without the `TRANSACTION` keyword.
- Aurora PostgreSQL does not use special data types for `UNICODE` data. All string types may use any character set and any relevant collation.
- Collations can be defined at the server, database, and column level (similar to SQL Server), but **not** at the table level.
- Aurora PostgreSQL does not support `DELETE <Table Name>` syntax where the `FROM` keyword is dropped. Add the `FROM` keyword to all `DELETE` statements.
- You can use multiple rows with `NULL` for a `UNIQUE` constraint (SQL Server allows only one). Aurora PostgreSQL follows the ANSI standard behavior.
- The `SERIAL` column property is similar to `IDENTITY` in SQL Server, but sequences are maintained differently. SQL Server caches a set of values in memory and records the last allocation on disk, so after a restart the sequence continues from where it left off (some cached values may be lost). In Aurora PostgreSQL, each restart resets the `SERIAL` seed to one increment interval larger than the largest existing value — sequence position is not maintained across service restarts.
- Parameter names do not require a preceding `@`. Declare local variables such as `SET schema.test = value` and read the value with `SELECT current_setting('username.test');`.
- Local parameter scope is not limited to the run scope. You can define or set a parameter in one statement, run it, and query it in a following batch.
- Error handling has fewer features, but for special requirements you can log or send alerts by inserting into tables or catching errors.
- Aurora PostgreSQL does not support the `MERGE` statement. Use the `REPLACE` statement and the `INSERT… ON DUPLICATE KEY UPDATE` statement as alternatives.
- You cannot concatenate strings with the `+` operator. Use the `CONCAT` function instead — e.g., `CONCAT('A', 'B')`.
- Aurora PostgreSQL does not support aliasing in the select list using `String Alias = Expression`. It treats this as a logical predicate (returns `0`/`FALSE`) and aliases the column with the full expression. Use the `AS` syntax instead. (This syntax has also been deprecated as of SQL Server 2008 R2.)
- Aurora PostgreSQL has a large, diverse set of string functions. Some of the more useful ones:
  - `TRIM` is not limited to full trim or spaces. Syntax: `TRIM([{BOTH | LEADING | TRAILING} [<remove string>] FROM] <source string>)`.
  - `LENGTH` in PostgreSQL is equivalent to `DATALENGTH` in T-SQL. `CHAR_LENGTH` is the equivalent of T-SQL `LENGTH`.
  - `SUBSTRING_INDEX` returns a substring from a string before the specified number of occurrences of the delimiter.
  - `FIELD` returns the index position of the first argument in the subsequent arguments.
  - `POSITION` returns the index position of the first argument within the second argument.
  - `REGEXP_MATCHES` provides support for regular expressions.
  - For more information, see [String Functions and Operators](https://www.postgresql.org/docs/13/functions-string.html).
- The `CAST` function is for casting between collation, not other data types. Use `CONVERT` for casting data types.
- Aurora PostgreSQL is much stricter than SQL Server about statement terminators. Always use a semicolon at the end of statements.
- You cannot use `CREATE PROCEDURE` syntax — use only `CREATE FUNCTION`. You can create a function that returns void.
- Beware of control characters when copying and pasting a script into Aurora PostgreSQL clients. Aurora PostgreSQL is much more sensitive to control characters than SQL Server, and they result in frustrating syntax errors that are hard to find.

## Conversion notes

- For T-SQL procedural conversion details (cursors, triggers, sequences/identity, stored procedures, error handling, transaction control), see `../tsql/`.
- For ANSI-standard SQL conversion details (joins, `GROUP BY`, `UNIQUE`/`NULL` semantics, `MERGE` alternatives, string functions), see `../ansi-sql/`.
