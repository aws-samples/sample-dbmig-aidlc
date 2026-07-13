# Migration Quick Tips — Oracle → Aurora MySQL

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tips.html

## Management
- A *database snapshot* in Aurora MySQL is the equivalent of an RMAN backup in Oracle.
- Aurora MySQL partitioning lacks many Oracle features: Partition Advisor, Preference Partitioning, Virtual Column-Based Partitioning, and Automatic List Partitioning.
- Aurora MySQL does not collect detailed key-value distribution statistics on tables (as Oracle does) — it only collects statistics on indexes.
- Use Amazon services (e.g. Lambda) to replicate functionality not provided by MySQL, such as sending email.
- Amazon RDS manages parameters and backups; it is useful for checking a parameter's value against its default and comparing across parameter groups.
- You can create replicas with just a few clicks to implement high availability.
- Aurora MySQL has no equivalent to database links — it can only query across databases within the same instance.

## SQL & stored programs
- No support for statement-level triggers or triggers on system events.
- Limited cursor status checks — when declaring cursors, create an explicit `HANDLER` object.
- Use `CALL` (not `EXECUTE`) to run a stored procedure or function.
- To run a string as a query, use Aurora MySQL Prepared Statements instead of `EXECUTE(<String>)`.
- Terminate `IF` blocks with `END IF`, and `WHILE..LOOP` loops with `END LOOP`.
- Auto-commit defaults to `ON` (unlike Oracle) — set it to `OFF` for Oracle-like behavior.
- Collations can be defined at the server, database, and column level — but not at the table level.
- The `DELETE <Table Name>` syntax that omits `FROM` (valid in Oracle) is invalid — add `FROM` to all `DELETE` statements.
- The `AUTO_INCREMENT` column property is the analog of Oracle `IDENTITY`.
- Error handling is less feature-rich than Oracle — for special needs, log or alert by inserting into tables or catching errors.
- No `MERGE` statement — use `REPLACE` and `INSERT…ON DUPLICATE KEY UPDATE` as alternatives.
- Cannot concatenate strings with the `||` operator — use `CONCAT()` instead.
- Stricter about statement terminators than Oracle — always use semicolons at the end of statements.
- No support for the `BFILE`, `ROWID`, and `UROWID` data types.
- Temporary tables are retained only for the session, and only the creating session can query them.
- No support for unused or virtual columns, and there is no workaround for virtual columns — combine views and functions instead.
- No support for materialized views — use views or summary tables instead.
- Explore AWS for features that can be replaced with Amazon services to ease maintenance and reduce cost.
- You can create multiple databases in a single instance — useful for consolidation projects.
- Beware of control characters when copying/pasting scripts into Aurora MySQL clients; it is far more sensitive to them than Oracle and they cause hard-to-find syntax errors.

## Conversion notes
- For detailed, object-level conversion guidance see the playbook references under
  `../sql-plsql/` (SQL and PL/SQL constructs: cursors, triggers, error handling, `MERGE`,
  prepared statements, sequences/`AUTO_INCREMENT`, string operators) and
  `../special-features/` (partitioning, materialized views, database links, virtual/unused
  columns, and other Oracle-specific capabilities and their Aurora MySQL workarounds).
