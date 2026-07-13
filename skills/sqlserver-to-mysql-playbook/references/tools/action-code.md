# AWS SCT Action Code Index

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.actioncode.html

**Conversion category:** N/A (tooling)
**SCT automation:** This page IS the master automation-level + action-code reference for every topic in the playbook.

## SQL Server
Reference of AWS SCT automation levels and action codes emitted when converting Microsoft SQL Server 2019 objects to Amazon Aurora MySQL. Each topic below lists its automation level and the specific action codes/messages SCT may raise.

### Automation level legend
| Level | Meaning |
|---|---|
| Full automation (5★) | Fully automatic conversion, no manual work needed. |
| High automation (4★) | Minor, simple manual conversions may be needed. |
| Medium automation (3★) | Low–medium complexity manual conversions may be needed. |
| Low automation (2★) | Medium–high complexity manual conversions may be needed. |
| Very low automation (1★) | High risk or complex manual conversions may be needed. |
| No automation | Not supported by SCT; manual conversion required. |

## MySQL
The action codes below indicate Aurora MySQL (v5.7-based) limitations relative to SQL Server. Note: Aurora MySQL 5.7 lacks window functions, CTEs, PIVOT/UNPIVOT, MERGE, synonyms, sequences, and check constraints (older note — newer MySQL 8.0 engines add several of these).

## Conversion notes

### Creating Tables — High automation (4★)
Auto-converts most `CREATE TABLE` constructs (names, columns, basic data types, constraints, defaults, PK/UNIQUE/FK). Changes may be needed for computed columns and global temporary tables.
- **659** — If you use recursion, make sure table variables (source) and temporary tables (target) have the same scope.
- **679** — AWS SCT replaced computed columns with triggers.
- **680** — MySQL doesn't support global temporary tables.

### Constraints — High automation (4★)
Auto-converts most constraints (PK, FK, NOT NULL, UNIQUE, defaults). Manual work for some FK cascading options; check constraints replaced with triggers; some `DateTime` default expressions and complex default expressions not auto-converted.
- **676** — MySQL doesn't support the `SET DEFAULT` referential constraint action.
- **677** — MySQL doesn't support functions/expressions as a default value for `BLOB` and `TEXT` columns.
- **678** — MySQL doesn't support check constraints.
- **825** — AWS SCT removed the default value of the column.
- **826** — AWS SCT can't convert the default value of the variable.
- **827** — AWS SCT can't convert default values.

### Data Types — High automation (4★)
Auto-converts most data type syntax/rules. Date/time paradigms differ and need manual verification/conversion. Strict testing recommended due to behavior differences.
- **601** — MySQL doesn't support including `BLOB` and `TEXT` columns in foreign keys.
- **706** — AWS SCT replaced the unsupported %s data type.
- **707** — AWS SCT can't convert the usage of a variable of the unsupported %s data type.
- **708** — AWS SCT can't convert the usage of the unsupported %s data type.
- **775** — Converted code might lose accuracy compared to the source code.
- **844** — AWS SCT expanded fractional seconds support for `TIME`, `DATETIME2`, and `DATETIMEOFFSET` values with up to 6 digits of precision.
- **919** — MySQL doesn't support the `DECIMAL` data type with scale greater than 30.

### Collations — High automation (4★)
Migrates most common cases incl. `NCHAR`/`NVARCHAR` (which don't exist in Aurora MySQL). Rewrites required for explicit `COLLATE` clauses unsupported by Aurora MySQL.
- **646** — MySQL doesn't support the `COLLATE` clause.

### Window Functions — No automation
Aurora MySQL 5.7 doesn't support window functions; SCT can't auto-convert. Use traditional SQL workarounds.
- **647** — MySQL doesn't support the analytic form of the %s function.
- **648** — MySQL doesn't support the `RANK` function.
- **649** — MySQL doesn't support the `DENSE_RANK` function.
- **650** — MySQL doesn't support the `NTILE` function.
- **754** — MySQL doesn't support `STDEV` functions with the `DISTINCT` clause.
- **755** — MySQL doesn't support `STDEVP` functions with the `DISTINCT` clause.
- **756** — MySQL doesn't support `VAR` functions with the `DISTINCT` clause.
- **757** — MySQL doesn't support `VARP` functions with the `DISTINCT` clause.

### PIVOT and UNPIVOT — No automation
Aurora MySQL 5.7 doesn't support `PIVOT`/`UNPIVOT`; SCT can't auto-convert.
- **905** — MySQL doesn't support `PIVOT` clauses for `SELECT` statements.
- **906** — MySQL doesn't support `UNPIVOT` clauses for `SELECT` statements.

### TOP and FETCH — High automation (4★)
Aurora MySQL supports `LIMIT … OFFSET`. SCT auto-converts most paging queries. `PERCENT` and `WITH TIES` need manual conversion.
- **604** — MySQL doesn't support the `PERCENT` argument in `TOP` clauses. SCT skips it.
- **605** — MySQL doesn't support the `WITH TIES` argument in `TOP` clauses. SCT skips it.
- **608** — MySQL doesn't support the `PERCENT` argument in `TOP` clauses of `INSERT` statements.
- **612** — MySQL doesn't support the `PERCENT` argument in `TOP` clauses of `UPDATE` statements.
- **621** — MySQL doesn't support the `PERCENT` argument in `TOP` clauses. SCT skips it.
- **830** — MySQL doesn't support `LIMIT` clauses with `IN`, `ALL`, `ANY`, or `SOME` subqueries.

### Common Table Expressions — No automation
Aurora MySQL 5.7 doesn't support CTEs; SCT can't auto-convert.
- **611** — MySQL doesn't support `WITH` queries in `UPDATE` statements.
- **619** — MySQL doesn't support query definitions for common table expressions.
- **839** — MySQL doesn't support query definitions for common table expressions.
- **840** — AWS SCT can't convert updated common table expressions.

### Cursors — Medium automation (3★)
Auto-converts common cursor ops (forward-only read-only; `DECLARE CURSOR`, `CLOSE CURSOR`, `FETCH NEXT`). Modifications through cursors and non-forward-only fetches need manual conversion.
- **618** — MySQL doesn't support `CURRENT OF` clauses for DML in a cursor loop body.
- **624** — MySQL doesn't support `CURRENT OF` clauses for DML in a cursor loop body.
- **625** — MySQL doesn't support the `CURSOR` data type as a procedure argument.
- **637** — MySQL doesn't support global cursors.
- **638** — MySQL doesn't support the `SCROLL` option in cursors.
- **639** — MySQL doesn't support dynamic cursors.
- **667** — MySQL doesn't support the %s option in cursors.
- **668** — MySQL doesn't support the `FIRST` option in cursors.
- **669** — MySQL doesn't support the `PRIOR` option in cursors.
- **670** — MySQL doesn't support the `ABSOLUTE` option in cursors.
- **671** — MySQL doesn't support the `RELATIVE` option in cursors.
- **692** — MySQL doesn't support cursor variables.
- **700** — AWS SCT can't convert the `KEYSET` option (MySQL can't change membership/order of rows for cursors).
- **701** — SCT doesn't convert `FAST_FORWARD` (default option for cursors in MySQL).
- **702** — SCT doesn't convert `READ_ONLY` (default option for cursors in MySQL).
- **703** — MySQL doesn't support the `SCROLL_LOCKS` option.
- **704** — MySQL doesn't support the `OPTIMISTIC` option for cursors.
- **705** — MySQL doesn't support the `TYPE_WARNING` option for cursors.
- **842** — MySQL doesn't support the %s option in cursors.

### Flow Control — High automation (4★)
Auto-converts loops, command blocks, delays. `GOTO` and `WAITFOR TIME` need manual conversion.
- **628** — MySQL doesn't support `GOTO` statements.
- **691** — MySQL doesn't support the `WAITFOR TIME` feature.

### Transaction Isolation — High automation (4★)
Aurora MySQL supports SQL:92 isolation levels (`READ UNCOMMITTED`, `READ COMMITTED`, `REPEATABLE READ`, `SERIALIZABLE`). Auto-converts these plus `BEGIN`/`COMMIT`/`ROLLBACK`. Manual for named, marked, delayed-durability transactions.
- **629** — MySQL doesn't support named transactions.
- **630** — MySQL doesn't support `WITH MARK` options.
- **631** — MySQL doesn't support distributed transactions.
- **632** — MySQL doesn't support rolling back named transactions.
- **633** — MySQL doesn't support the `DELAYED_DURABILITY` option.
- **916** — MySQL doesn't support the `SNAPSHOT` transaction isolation level.

### Stored Procedures — High automation (4★)
Auto-converts most procedures. Manual for `RETURN` values and less-common `EXECUTE` options (`RECOMPILE`, `RESULT SETS`).
- **640** — MySQL doesn't support `EXECUTE` with the `WITH RECOMPILE` option.
- **641** — MySQL doesn't support `EXECUTE` with the `RESULT SETS UNDEFINED` option.
- **642** — MySQL doesn't support `EXECUTE` with the `RESULT SETS NONE` option.
- **643** — MySQL doesn't support `EXECUTE` with the `RESULT SETS DEFINITION` option.
- **689** — MySQL doesn't support `RETURN` statements used to return values from a procedure.
- **695** — MySQL doesn't support the call of a procedure as a variable.

### Triggers — Medium automation (3★)
Aurora MySQL supports `BEFORE`/`AFTER` triggers for `INSERT`/`UPDATE`/`DELETE`. Manual inspection needed: Aurora MySQL triggers run once per row, not once per statement.
- **686** — MySQL doesn't support triggers with the `FOR STATEMENT` clause.

### GROUP BY — High automation (4★)
Auto-converts `GROUP BY` except `CUBE` and `GROUPING SETS` (need manual workarounds).
- **654** — MySQL doesn't support the `GROUP BY CUBE` option.
- **655** — MySQL doesn't support `GROUP BY GROUPING SETS` clauses.

### Identity and Sequences — Medium automation (3★)
Auto-converts `IDENTITY` → `AUTO_INCREMENT`. Manual for explicit SEED/INCREMENT columns not part of the PK and table-independent `SEQUENCE` objects.
- **696** — MySQL doesn't support identity columns with seed and increment.
- **697** — MySQL doesn't support identity columns outside the primary key.
- **732** — MySQL doesn't support identity columns in compound primary keys.
- **815** — MySQL doesn't support sequences.
- **841** — MySQL doesn't support numeric(x,0)/decimal(x,0) in `AUTO_INCREMENT` columns; SCT replaced with a compatible type.
- **920** — MySQL doesn't support identity columns of `DECIMAL`/`NUMERIC` with precision greater than 19.

### Error Handling — Medium automation (3★)
Different paradigms (MySQL uses condition + handler objects). Auto-converts basic constructs; strict validation recommended. Manual for `THROW` with variables and built-in messages.
- **729** — AWS SCT can't convert `THROW` operators with variables.
- **730** — AWS SCT truncated the error code.
- **733** — MySQL doesn't support `PRINT` procedures.
- **814** — AWS SCT can't convert the `RAISERROR` operator with messages from the `sys.messages` view.
- **837** — MySQL uses a different approach to handle errors compared to the source code.

### Date and Time Functions — High automation (4★)
Auto-converts most date/time functions despite syntax differences. Watch data types, time-zone awareness, locale handling. Manual for millisecond, nanosecond, and time-zone offset options.
- **759** — MySQL doesn't support `DATEADD` with the nanosecond date part.
- **760** — MySQL doesn't support `DATEDIFF` with the week date part.
- **761** — MySQL doesn't support `DATEDIFF` with the millisecond date part.
- **762** — MySQL doesn't support `DATEDIFF` with the nanosecond date part.
- **763** — MySQL doesn't support `DATENAME` with the millisecond date part.
- **764** — MySQL doesn't support `DATENAME` with the nanosecond date part.
- **765** — MySQL doesn't support `DATENAME` with the TZoffset date part.
- **767** — MySQL doesn't support `DATEPART` with the nanosecond date part.
- **768** — MySQL doesn't support `DATEPART` with the TZoffset date part.
- **773** — AWS SCT can't convert arithmetic operations with dates.

### User-Defined Functions — Medium automation (3★)
Aurora MySQL supports only scalar UDFs (auto-converted). Table-valued UDFs (inline and multi-statement) need manual conversion (workarounds via views/derived tables).
- **777** — SCT can't emulate a table-valued function because a column from the current query is used as a function parameter.
- **822** — MySQL doesn't support table-valued functions in views.

### User-Defined Types — Medium automation (3★)
Aurora MySQL 5.7 doesn't support UDTs or table-valued parameters. SCT converts standard UDTs by replacing with base types; manual for user-defined table types.
- **690** — MySQL doesn't support table types.

### Synonyms — No automation
Aurora MySQL 5.7 doesn't support synonyms; SCT can't auto-convert.
- **792** — MySQL doesn't support synonyms.

### XML and JSON — High automation (4★)
Aurora MySQL has minimal XML support but a native JSON type and 25+ JSON functions. Auto-converts common basic XML functions. Manual for `EXPLICIT` mode and subquery usage.
- **817** — AWS SCT can't convert `FOR XML` clauses with `EXPLICIT` mode specified.
- **818** — AWS SCT can't convert correlated subqueries with `FOR XML` clauses.
- **843** — AWS SCT can't convert `FOR XML` statements in functions.

### Table Joins — High automation (4★)
Auto-converts `INNER`, `OUTER`, `CROSS` joins. `APPLY`/`LATERAL` joins not supported by Aurora MySQL — manual conversion.
- **831** — MySQL doesn't support `CROSS APPLY`/`OUTER APPLY` where the subquery references a column of the attachable table.

### MERGE — No automation
Aurora MySQL 5.7 doesn't support `MERGE`; SCT can't auto-convert (manual usually straightforward).
- **832** — MySQL doesn't support `MERGE` statements.

### Query Hints — Medium automation (3★)
Basic hints (e.g., index hints) auto-converted except in DML. Recommendation: remove all hints before testing, then apply selectively as a last resort. Plan guides not supported by Aurora MySQL.
- **610** — MySQL doesn't support hints in `INSERT`. SCT skips `WITH(Table_Hint_Limited)`.
- **617** — MySQL doesn't support hints in `UPDATE`. SCT skips `WITH(Table_Hint_Limited)`.
- **623** — MySQL doesn't support hints in `DELETE`. SCT skips `WITH(Table_Hint_Limited)`.
- **823** — MySQL doesn't support table hints in DML statements.

### Full-Text Search — No automation
Migrating full-text indexes requires a full rewrite of creation/management/query code; SCT can't auto-convert.
- **687** — MySQL doesn't support the `CONTAINS` predicate.
- **688** — MySQL doesn't support the `FREETEXT` predicate.

### Indexes — High automation (4★)
Auto-converts basic non-clustered indexes. User-defined clustered indexes not supported (Aurora MySQL always clusters on PK). Filtered indexes, included columns, and some SQL Server-specific index options need manual conversion.
- **602** — MySQL has reached the limit of the internal InnoDB maximum key length.
- **681** — MySQL doesn't support clustered indexes.
- **682** — MySQL doesn't support the `INCLUDE` clause in indexes.
- **683** — MySQL doesn't support the `WHERE` clause in indexes.
- **684** — MySQL doesn't support the `WITH` clause in indexes.

### Partitioning — No automation
Physical partitioning aspects (file groups) don't apply to Aurora MySQL. Aurora MySQL offers richer partitioning (hash, subpartitioning) but SCT doesn't auto-convert partitions.
- **907** — AWS SCT can't convert tables arranged in several partitions.

### Backup — No automation
Paradigm shift to PaaS: Amazon RDS provides continuous backup with point-in-time restore up to 35 days. SCT doesn't auto-convert backups.
- **903** — MySQL doesn't support functionality similar to SQL Server Backup.

### SQL Server Database Mail — No automation
Aurora MySQL has no native support for sending mail from the database.
- **900** — MySQL doesn't support functionality similar to SQL Server Database Mail.

### SQL Server Agent — No automation
No external cross-instance scheduler equivalent. Aurora MySQL has a native in-database scheduler limited to cluster scope. SCT can't auto-convert Agent jobs/alerts.
- **902** — MySQL doesn't support functionality similar to SQL Server Agent.

### Linked Servers — No automation
Aurora MySQL doesn't support remote data access from the database. SCT can't auto-convert commands on linked servers.
- **645** — MySQL doesn't support running pass-through commands on linked servers.

### Views — High automation (4★)
MySQL views are similar to SQL Server views with slight differences (indexing, triggers on views, query definition).
- **779** — AWS SCT can't convert `SELECT` statements that contain a subquery in the `FROM` clause.
