# AWS SCT Action Code Index

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tools.actioncode.html

**Conversion category:** N/A (reference index of per-feature conversion categories)
**SCT automation:** This page defines the automation-level scale and lists action codes per topic.

## Automation level scale

| Stars / icon | Level | Description |
|---|---|---|
| ★★★★★ | **Full automation** | AWS SCT performs fully automatic conversion; no manual conversion needed. |
| ★★★★ | **High automation** | Minor, simple manual conversions may be needed. |
| ★★★ | **Medium automation** | Low–medium complexity manual conversions may be needed. |
| ★★ | **Low automation** | Medium–high complexity manual conversions may be needed. |
| ★ | **Very low automation** | High risk or complex manual conversions may be needed. |
| (none) | **No automation** | Not currently supported by AWS SCT; manual conversion required. |

The following sections list AWS SCT action codes for topics covered in the playbook.

## Creating tables — ★★★★ High automation

AWS SCT automatically converts the most commonly used `CREATE TABLE` constructs because Oracle and Aurora MySQL support entry-level ANSI compliance: table names, schema/database, column names, basic column data types, column and table constraints, column default values, primary, UNIQUE, and foreign keys. Some changes may be required for computed columns and global temporary tables.

| Code | Message |
|---|---|
| 73 | MySQL doesn't support the `IDENTITY` statement with `MAXVALUE`, `MINVALUE`, or `CYCLE` options, or with an `INCREMENT BY` value different from 1. |
| 74 | MySQL doesn't support `AUTO_INCREMENT` statements without the primary key option on the same column. |
| 190 | MySQL doesn't support the `COLUMN_VALUE` pseudocolumn. |
| 191 | MySQL doesn't support the `OBJECT_ID` pseudocolumn. |
| 192 | MySQL doesn't support the `ORA_ROWSCN` pseudocolumn. |
| 193 | MySQL doesn't support the `ROWID` pseudocolumn. |
| 198 | MySQL doesn't support global temporary tables. |
| 199 | MySQL doesn't support clustered tables. |
| 200 | MySQL doesn't support external tables. |
| 209 | AWS SCT uses triggers to emulate virtual columns because MySQL doesn't support virtual columns. |
| 210 | AWS SCT uses triggers to emulate the use of functions/expressions as default value in `CREATE TABLE`. |
| 215 | MySQL doesn't support virtual columns with unsupported built-in functions. |
| 245 | MySQL doesn't support views with nested table columns. |
| 296 | AWS SCT can't convert tables that aren't valid. |
| 327 | MySQL doesn't support the objects column. |
| 348 | MySQL doesn't support global temporary tables. |

## Constraints — ★★★★ High automation

Automatically converts most constraints (entry-level ANSI): primary keys, foreign keys, null, unique, and default constraints (with exceptions). Manual conversion for some FK cascading options. AWS SCT replaces check constraints with triggers; some `DateTime` default expressions and complex default expressions can't be auto-converted.

| Code | Message |
|---|---|
| 202 | MySQL doesn't support foreign keys with different types of columns or with referenced columns. |
| 203 | AWS SCT can't convert foreign keys with the `SET NULL` action for columns that have the `NOT NULL` constraint. |
| 204 | AWS SCT can't convert foreign keys with `BLOB` and `TEXT` columns. |
| 220 | MySQL doesn't support the record type. |
| 325 | AWS SCT uses triggers to emulate check constraints because MySQL doesn't support them. |
| 326 | MySQL doesn't support constraints with status set to `DISABLED`. |
| 591 / 593 | AWS SCT can't convert the `ROWID` usage. This object uses the `ROWID` column from the %s table. |

## Data types — ★★★★ High automation

Data type syntax and rules are similar; AWS SCT auto-converts most. Date/time handling paradigms differ and require manual verification or conversion. Manual verification and strict testing strongly recommended due to behavior differences.

| Code | Message |
|---|---|
| 25 | MySQL doesn't support assignment values for variables of the `INTERVAL` datatype. |
| 28 | AWS SCT can't convert the variable declaration of the %s unsupported data type. |
| 29 | AWS SCT can't convert the reference of the %s unsupported data type. |
| 30 | AWS SCT can't convert the usage of the %s unsupported data type. |
| 33 | MySQL doesn't support fractional seconds for `TIMESTAMP` literals. |
| 212 | MySQL doesn't support the `BFILE` data type. |

## Common table expressions — No automation

Aurora MySQL 5.7 doesn't support CTEs. AWS SCT can't auto-convert; use traditional SQL workarounds.

| Code | Message |
|---|---|
| 127 | MySQL doesn't support recursive `WITH` clauses. |

## Cursors — ★★★ Medium automation

Auto-converts the most common cursor operations: forward-only read-only cursors, `DECLARE CURSOR`, `CLOSE CURSOR`, `FETCH NEXT`. Modifications through cursors and non-forward-only fetches (unsupported by Aurora MySQL) require manual conversion.

| Code | Message |
|---|---|
| 31 | AWS SCT can't convert `CURSOR` expressions. |
| 84 | AWS SCT doesn't convert the `SQL%ISOPEN` cursor attribute because this is the default behavior in MySQL. |
| 85 | MySQL doesn't support the `SQL%BULK_ROWCOUNT` cursor attribute. |
| 297 | MySQL doesn't support `%ROWTYPE` attributes. |
| 330 | MySQL doesn't support global cursors. AWS SCT replaces global cursors with local cursors. |
| 337 | MySQL doesn't support variables of the `SYS_REFCURSOR` type. |
| 343 | AWS SCT can't convert `SELECT` statements for cursors. |
| 354 | AWS SCT can't convert dynamic SQL for the `REF_CURSOR` variable. |
| 596 | Converted code might produce different results. If `SQL%ROWCOUNT` refers to `INSERT`/`DELETE`, use `FOUND_ROWS()` instead of `ROW_COUNT()`. |
| 598 | MySQL doesn't support `RETURN` clauses in cursors. |

## Transaction isolation — ★★★★ High automation

Aurora MySQL supports SQL:92 isolation levels `READ UNCOMMITTED`, `READ COMMITTED`, `REPEATABLE READ`, `SERIALIZABLE`; all auto-converted. Also converts `BEGIN`, `COMMIT`, `ROLLBACK`. Manual conversion for named, marked, and delayed durability transactions (unsupported by Aurora MySQL).

| Code | Message |
|---|---|
| 235 | MySQL doesn't support `PRAGMA` options. |
| 302 | MySQL doesn't support `NOWAIT` clauses in `LOCK TABLE` statements. |
| 346 | MySQL doesn't support `LOCK TABLE` statements inside stored procedures. |
| 350 | AWS SCT can't convert statements such as `START TRANSACTION`, `COMMIT`, or `ROLLBACK`. |

## Stored procedures — ★★★★ High automation

Very similar functionality; auto-converts Oracle stored procedures. Manual conversion for procedures using `RETURN` values and some less-common `EXECUTE` options such as `RECOMPILE` and `RESULTS SETS`.

| Code | Message |
|---|---|
| 27 | The package body doesn't include source code. |
| 152 | Converted code might not cover all built-in exception names. |
| 234 | MySQL doesn't support the `EXCEPTION` declaration. |
| 253 | MySQL doesn't support the %s function with two parameters. |
| 266 | MySQL doesn't support the %s function with analytic clauses. |
| 329 | MySQL doesn't support `RAISE` statements. |
| 331 | MySQL doesn't support global user-defined exceptions. |
| 333 | MySQL doesn't support exception blocks in initialization blocks in packages. |
| 335 | MySQL doesn't support `GOTO` operators. |
| 340 | MySQL doesn't support the %s function. |
| 342 | MySQL doesn't support the %s exception. |
| 345 | Converted code might not cover all conditions. |
| 350 | AWS SCT can't convert statements such as `START TRANSACTION`, `COMMIT`, or `ROLLBACK`. |
| 590 | AWS SCT converted the function as procedure. |

## Triggers — ★★★ Medium automation

Aurora MySQL supports `BEFORE`/`AFTER` triggers for `INSERT`, `UPDATE`, `DELETE`. They differ substantially from Oracle triggers, but AWS SCT can migrate most with minimal changes. Manual inspection may be required because Aurora MySQL triggers run once per row, not once per statement.

| Code | Message |
|---|---|
| 236 | MySQL doesn't support `INSTEAD OF` triggers. |
| 237 | MySQL doesn't support statement triggers. |
| 238 | MySQL doesn't support `REFERENCING` clauses. |
| 239 | MySQL doesn't support triggers with `WHEN` conditions. |
| 240 | MySQL doesn't support triggers on nested table columns in views. |
| 241 | MySQL doesn't support triggers with `FOLLOWS` and `PRECEDES` clauses. |
| 242 | MySQL doesn't support compound triggers. |
| 243 | MySQL doesn't support `UPDATE OF` clauses. |
| 244 | MySQL doesn't support conditional predicates. |
| 306 | AWS SCT can't convert a trigger that isn't valid. |
| 310 | MySQL doesn't support triggers for views. |
| 311 | MySQL doesn't support system triggers. |
| 312 | MySQL doesn't support `DISABLED` clauses. |
| 313 | MySQL doesn't support action-type clauses in triggers. |
| 314 | MySQL doesn't support cross edition triggers. |
| 316 | MySQL doesn't support the apply-server-only property. |
| 317 | MySQL doesn't support `PARENT` referencing clauses. |
| 415 | MySQL doesn't support system triggers. |
| 524 | MySQL doesn't support triggers for multiple events. |
| 588 | MySQL doesn't support multiple triggers for a single event. AWS SCT merged triggers into one trigger. |

## Sequences — ★ Very low automation

Oracle `IDENTITY` and Aurora MySQL `AUTO_INCREMENT` syntax differ significantly but AWS SCT can auto-convert. Manual conversion for explicit `SEED`/`INCREMENT` auto-enumeration columns that aren't part of the primary key, and for table-independent `SEQUENCE` objects.

| Code | Message |
|---|---|
| 341 | MySQL doesn't support sequences. |

## Date and time functions — ★★★★ High automation

Auto-converts most common date/time functions despite large syntax differences. Watch for differences in data types, time-zone awareness, and locale handling. Less-common options (millisecond, nanosecond, time-zone offsets) require manual conversion.

| Code | Message |
|---|---|
| 213 | AWS SCT expanded fractional-seconds support for `TIME`, `DATETIME`, `TIMESTAMP` up to 6 digits of precision. |
| 214 | MySQL doesn't support data types that store time zone information. `DATETIME` stores timestamps in the MySQL server time zone. |
| 216 | AWS SCT expanded fractional seconds (up to 6 digits); MySQL doesn't support data types storing time zone information. |

## User-defined types — ★★★ Medium automation

Aurora MySQL 5.7 doesn't support user-defined types or table-valued parameters. AWS SCT converts standard UDTs by replacing them with base types; manual conversion required for user-defined table types (used for table-valued parameters in stored procedures).

| Code | Message |
|---|---|
| 196 | MySQL doesn't support object tables. |
| 218 | MySQL doesn't support user types. |

## Synonyms — No automation

Aurora MySQL 5.7 doesn't support synonyms. AWS SCT can't auto-convert.

| Code | Message |
|---|---|
| 352 | MySQL doesn't support synonyms. AWS SCT replaces synonyms with fully-qualified object names. |

## XML — ★★★★ High automation

Aurora MySQL has minimal XML support but offers a native JSON data type and 25+ JSON functions. Most common basic XML functions auto-migrate. Options such as `EXPLICIT` (in functions or with subqueries) require manual conversion.

| Code | Message |
|---|---|
| 194 | MySQL doesn't support `XMLTYPE` tables. |
| 195 | MySQL doesn't support the `XMLDATA` pseudocolumn. |
| 303 | MySQL doesn't support the `XMLTable` function. |

## MERGE — No automation

Aurora MySQL 5.7 doesn't support `MERGE`. AWS SCT can't auto-convert; manual conversion is straightforward in most cases.

| Code | Message |
|---|---|
| 102 | MySQL doesn't support `MERGE` statements. |

## Query hints — ★★★ Medium automation

Auto-converts basic query hints (e.g., index hints) except for DML statements. Oracle-specific optimizations may be inapplicable to the new optimizer. Recommended: start testing with all hints removed, then selectively apply as a last resort. Plan guides aren't supported by Aurora MySQL.

| Code | Message |
|---|---|
| 103 | AWS SCT can't convert hints. MySQL doesn't support the %s hint. |

## Indexes — ★★★★ High automation

Auto-converts basic non-clustered indexes (the most common). User-defined clustered indexes aren't supported (always created for the primary key). Filtered indexes, indexes with included columns, and some Oracle-specific options require manual conversion.

| Code | Message |
|---|---|
| 205 | MySQL has reached the limit of the internal InnoDB maximum key length. |
| 206 | MySQL doesn't support bitmap indexes. |
| 207 | MySQL doesn't support function indexes. |
| 208 | MySQL doesn't support domain indexes. |
| 328 | AWS SCT can't convert indexes that aren't valid. |

## Partitioning — ★★★ Medium automation

Because Aurora MySQL stores each table in its own file (managed by AWS, not modifiable), Oracle's physical partitioning aspects don't apply. Due to vast differences, AWS SCT doesn't auto-convert table/index partitions — manual conversion required.

| Code | Message |
|---|---|
| 201 | MySQL doesn't support partition types implemented in your source code. |
| 699 | MySQL doesn't support not-allowed partition functions. |

## Materialized views — No automation

Aurora MySQL 5.7 doesn't support materialized views. AWS SCT can't auto-convert.

| Code | Message |
|---|---|
| 94 | MySQL doesn't support materialized views. |
| 95 | MySQL doesn't support the usage of materialized views. |

## Views — ★★★★ High automation

Basic `CREATE VIEW` syntax is almost identical, but some sub-options differ significantly and require manual migration.

| Code | Message |
|---|---|
| 75 | MySQL doesn't support read-only views. |
| 93 | MySQL doesn't support `UPDATE` statements for views. |
| 97 | MySQL doesn't support `DELETE` statements for views. |
| 320 | AWS SCT can't convert a view that isn't valid. |
| 321 | MySQL doesn't support object views. |
| 323 | MySQL doesn't support subviews under a superview. |
| 324 | MySQL doesn't support editioning views. |
| 583 | MySQL doesn't support constraints for views. |

## UTL_Mail and UTL_SMTP — No automation

Aurora MySQL doesn't provide native support for sending emails from the database.

| Code | Message |
|---|---|
| 81 | MySQL doesn't support sending SMS notifications. |
| 82 | MySQL doesn't support sending emails. |

## Database Links — No automation

Aurora MySQL doesn't support remote data access. Cross-schema connectivity is trivial, but connecting to other instances requires a custom solution. AWS SCT can't auto-convert database links.

| Code | Message |
|---|---|
| 600 | MySQL doesn't support the usage of database links. |

## PLSQL — ★★★★ High automation

Auto-converts most common SQL statements (entry-level ANSI). Some changes needed for DML related to `ERROR LOG`, subquery, and partitions.

| Code | Message |
|---|---|
| 63 | AWS SCT can't convert `UPDATE` statements with multiple-column subqueries in `SET` clauses. |
| 64 | MySQL doesn't support `UPDATE` statements with `ERROR LOG` clauses. |
| 65 | MySQL doesn't support `UPDATE` statements for subqueries. |
| 66 | MySQL doesn't support `UPDATE` statements for `RETURNING INTO` clauses. |
| 67 | MySQL doesn't support `DELETE` statements with `ERROR LOG` clauses. |
| 68 | MySQL doesn't support `DELETE` statements for subqueries. |
| 69 | MySQL doesn't support `DELETE` statements for `RETURNING INTO` clauses. |
| 70 | MySQL doesn't support `INSERT` statements with `ERROR LOG` clauses. |
| 71 | MySQL doesn't support `INSERT` statements for subqueries. |
| 72 | MySQL doesn't support `INSERT` statements for `RETURNING INTO` clauses. |
| 77 | MySQL doesn't support `PIVOT` clauses for `SELECT` statements. |
| 78 | MySQL doesn't support `UNPIVOT` clauses for `SELECT` statements. |
| 87 | MySQL doesn't support `RETURNING BULK COLLECT INTO` clauses. |
| 89 | MySQL doesn't support `INSERT` statements for views. |
| 90 | MySQL doesn't support `INSERT` statements for subpartitions. |
| 122 | MySQL doesn't support hierarchical queries. |
| 125 | MySQL doesn't support `GROUPING SETS` statements. |
| 128 | MySQL doesn't support `ORACLE FLASHBACK VERSION QUERY`. |
| 138 | MySQL doesn't support `FOR UPDATE OF` clauses. |
| 139 | MySQL doesn't support `FOR UPDATE SKIP LOCKED` clauses. |
| 140 | MySQL doesn't support `BULK COLLECT INTO` clauses. |
| 141 | MySQL doesn't support `ORDER BY … NULLS FIRST` clauses. |
| 143 | MySQL doesn't support `FOR UPDATE NOWAIT` clauses. |
| 144 | MySQL doesn't support `FOR UPDATE WAIT` clauses. |
| 585 | AWS SCT can't convert outer join inside a correlated query. |
| 594 | MySQL doesn't support `LATERAL`, `CROSS APPLY`, and `OUTER APPLY` correlated inline views. |
| 599 | MySQL doesn't support `CURRENT OF` clauses for DML queries in the body of a cursor loop. |

## EXECUTE IMMEDIATE — ★★★★ High automation

Major difference: in MySQL, `EXECUTE IMMEDIATE` must be used after a `PREPARE` command. Running SQL with results and bind variables, and running anonymous blocks, aren't supported.

| Code | Message |
|---|---|
| 88 | MySQL doesn't support `EXECUTE IMMEDIATE` statements with `BULK COLLECT`. |
| 334 | MySQL doesn't support `EXECUTE IMMEDIATE` dynamic SQL statements. |
| 336 | MySQL doesn't support `EXECUTE IMMEDIATE` dynamic SQL statements with the %s clause. |

## DBMS_OUTPUT — No automation

Aurora MySQL doesn't provide native support for the `dbms_output` procedure. Use the `RAISE` command instead.

| Code | Message |
|---|---|
| 332 | MySQL doesn't support the `dbms_output.put_line` procedure. |
| 349 | MySQL doesn't support the `dbms_output.put` procedure. |

## Conversion notes

- Action codes shown in the AWS SCT assessment report map to specific manual-conversion guidance in the corresponding playbook topic pages.
- "No automation" topics (CTEs, synonyms, MERGE, materialized views, UTL_Mail/UTL_SMTP, database links, DBMS_OUTPUT) always require manual work.
- Several Oracle features are emulated by AWS SCT via **triggers** in Aurora MySQL: virtual columns (209), function/expression defaults (210), and check constraints (325).
- Sequences are the lowest-automation table feature (★) because Aurora MySQL lacks standalone `SEQUENCE` objects — only `AUTO_INCREMENT` tied to a primary key.
- Aurora MySQL trigger semantics differ fundamentally: per-row execution (not per-statement), no `INSTEAD OF`/statement/compound triggers — always review converted triggers.
