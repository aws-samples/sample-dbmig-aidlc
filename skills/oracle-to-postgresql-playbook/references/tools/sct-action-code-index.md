# AWS SCT Action Code Index

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tools.actioncode.html

**Conversion category:** N/A (cross-cutting index of automation levels and action codes)
**SCT automation:** This page defines the automation-level legend used throughout the playbook and lists per-topic SCT action codes.

## Automation level legend

| Icon | Level | Description |
|---|---|---|
| ★★★★★ | Full automation | AWS SCT performs fully automatic conversion; no manual conversion needed. |
| ★★★★ | High automation | Minor, simple manual conversions may be needed. |
| ★★★ | Medium automation | Low–medium complexity manual conversions may be needed. |
| ★★ | Low automation | Medium–high complexity manual conversions may be needed. |
| ★ | Very low automation | High risk or complex manual conversions may be needed. |
| (none) | No automation | Not currently supported by AWS SCT; manual conversion required. |

## Oracle
The action codes below are emitted by AWS SCT (and AWS DMS) when converting Oracle objects. Each section's star rating indicates the overall automation level for that feature category in Oracle→Aurora PostgreSQL migration.

## PostgreSQL
The codes describe what the Aurora PostgreSQL target does or does not support, and where manual rewrite is required. Action codes by topic:

### SQL — ★★★ (Medium)
Most common SQL auto-converts (both engines are entry-level ANSI compliant); changes may be needed for `ERROR LOG`, subquery, or partition DML.
- 5024 — PostgreSQL doesn't support `INSERT` with a partition name/partition key value.
- 5064 — No `UPDATE` with `ERROR LOG` option.
- 5065 — No `UPDATE` for subqueries.
- 5067 — No `DELETE` with `ERROR LOG` option.
- 5068 — No `DELETE` for subqueries.
- 5070 — No `INSERT` with `ERROR LOG` option.
- 5071 — No `INSERT` for subqueries.
- 5087 — No `RETURNING BULK COLLECT INTO`.
- 5088 — No `EXECUTE IMMEDIATE` with `BULK COLLECT`.
- 5090 — No `INSERT` for a `SUBPARTITION`.
- 5098 — No `DELETE` for a `PARTITION`.
- 5126 — No `MODEL` statements.
- 5139 — No `FOR UPDATE SKIP LOCKED`.
- 5140 — No `BULK COLLECT INTO`.
- 5144 — No `FOR UPDATE WAIT`.
- 5334 — SCT can't convert dynamic SQL.
- 5352 — No synonyms.
- 5353 — No usage of synonyms.
- 5557 — No `GROUPING SETS`, `CUBE`, `ROLLUP`.
- 5558 — No `UPDATE` for partitions.
- 5578 — SCT can't convert the `SELECT` statement.
- 5585 — SCT can't convert outer joins into correlated subqueries.
- 5608 — SCT can't convert `UPDATE` with a subquery returning multiple columns in the `SET` clause.
- 5663 — No explicit autonomous transactions.

### Creating tables — ★★★★ (High)
Auto-converts table/column names, schema, basic data types, constraints, defaults, primary/unique/foreign keys. Manual work may be needed for computed columns and global temporary tables.
- 5196 — No `OBJECT TABLE`.
- 5198 — No `GLOBAL TEMPORARY TABLE`.
- 5199 — No `CLUSTERED TABLE`.
- 5200 — No `EXTERNAL TABLES`.
- 5201 — Partition type not supported.
- 5212 — No `BFILE` data type.
- 5213 — PostgreSQL ensures microsecond support for time/datetime/timestamp.
- 5298 — No `DROP STORAGE` in `TRUNCATE`.
- 5299 — No `REUSE STORAGE` in `TRUNCATE`.
- 5300 — No `PRESERVE` in `TRUNCATE`.
- 5301 — No `PURGE` in `TRUNCATE`.
- 5326 — No status definitions in `CREATE` for triggers/constraints.
- 5348 — No nested tables.
- 5550 — No `ROWID` data type.
- 5551 — No `UROWID` data type.
- 5552 / 5553 — Microsecond support for time/datetime/timestamp.
- 5554 — No virtual columns.
- 5581 — No index-organized tables.
- 5620 — SCT extension pack doesn't support `DELETE ROWS` for `ON COMMIT` on global temp tables.
- 5621 — Ensure the unique constraint for the %s field exists.
- 5635 — SCT doesn't support Oracle-specific formatting settings.
- 5659 — SCT can't convert tables with columns of the %s data type.

### Data types — ★★★★ (High)
Syntax is similar; most auto-convert. Date/time paradigms differ — manual verification and strict testing recommended.
- 5028 / 5029 / 5030 — Can't convert object definitions/usage with unsupported %s data type.
- 5212 — No `BFILE`.
- 5550 — No `ROWID`.
- 5551 — No `UROWID`.
- 5572 — No object type methods.
- 5595 / 5597 — Can't convert `ROWID` usage referencing the %s table.
- 5598 — No `ROWID`.
- 5609 — Can't convert unsupported %s data type.
- 5613 — Can't convert multi-dimensional arrays.
- 5636 — Can't convert `VARRAY of VARRAY`.
- 5644 — Can't convert array/nested-table assignment that includes a nested record.

### Character set — ★★★★ (High)
Character-set granularity differs significantly in some cases.
- 5623 — SCT doesn't support uuencoding.

### Cursors — ★★★ (Medium)
PL/pgSQL cursors (always of `refcursor` type) provide row iteration; some options aren't auto-converted.
- 5031 — Can't convert `CURSOR` expressions.
- 5040 — Can't convert `SHARING` clauses.
- 5042 — No cursors of a specified type.
- 5117 — Can't convert cursor attributes (%s).
- 5225 — No `TYPE … IS REF CURSOR` declarations.
- 5226 — No `TYPE … IS REF CURSOR` usage.
- 5330 — No global cursors.
- 5559 — No `RETURN TYPE` for cursors.
- 5560 — No `PROGRAM_ERROR` exceptions.
- 5561 — Can't convert pre-defined exception %s.
- 5580 — Exception block in converted code is empty.
- 5599 — No `SQLERRM` references outside an exception handler.
- 5600 — No `SQLERRM` references with a specified parameter value.
- 5601 — No `SQLCODE` references outside an exception handler.
- 5602 — PostgreSQL error code type incompatible with number-type variables.
- 5604 — No global cursors; SCT converts them to local cursors.
- 5612 — Can't convert `FETCH` for a global parameterized cursor before the cursor variable is opened.

### Flow control — ★★★★ (High)
Loops, command blocks, delays auto-convert. `GOTO` and conditional compilation need manual conversion.
- 5335 — No `GOTO` operators.
- 5603 — No conditional compilation.

### Transaction isolation — ★★★★ (High)
Supports the four SQL:92 isolation levels (`READ UNCOMMITTED`, `READ COMMITTED`, `REPEATABLE READ`, `SERIALIZABLE`); `BEGIN/COMMIT/ROLLBACK` auto-convert. Manual work for named/marked/delayed-durability transactions (unsupported).
- 5350 — Can't convert statements that explicitly apply/cancel a transaction.
- 5611 — No `SAVEPOINT` / `ROLLBACK TO SAVEPOINT` inside routines.

### Stored procedures — ★★★ (Medium)
Aurora PostgreSQL functions are similar and mostly auto-convert. Manual for procedures using `RETURN` values and some `EXECUTE` options (`RECOMPILE`, `RESULTS SETS`).
- 5027 — Package body has no source code.
- 5340 — No %s function.
- 5579 — Verify the second parameter of %s is processed correctly.
- 5584 — %s function depends on time zone settings.
- 5607 — Can't convert Java stored routine.
- 5616 — Can't convert `TABLE` functions.
- 5617 — Doesn't fully support m/x match or subexpression parameters for regex.
- 5624 — Converted code may misbehave due to bind variable names.
- 5625 — No parameters in an anonymous block.
- 5626 — Can't convert %s function.
- 5627 — Converted code may misbehave due to user-defined functions.
- 5628 / 5633 — Converted code may misbehave due to dynamic SQL.
- 5629 — Doesn't fully support `DBMS_SQL` package.
- 5630 — Can't convert `DBMS_SQL` package functions.
- 5634 — Can't convert user-defined functions with `OUT`/`INOUT` parameters.

### Triggers — ★★★ (Medium)
Supports `BEFORE`/`AFTER` triggers for `INSERT`/`UPDATE`/`DELETE`; differs substantially from Oracle but most cases migrate with minimal change.
- 5238 — No `REFERENCING` clauses.
- 5240 — No triggers on nested table columns in views.
- 5241 — No `FOLLOWS`/`PRECEDES` clauses.
- 5242 — No `COMPOUND TRIGGER`.
- 5243 — Trigger always created under the table's schema — review converted code.
- 5306 — Can't convert an invalid trigger.
- 5311 / 5415 — No system triggers.
- 5313 — No action-type clauses in triggers.
- 5317 — No `PARENT` referencing clauses.
- 5556 — No conditional predicates.

### Sequences — ★★★ (Medium)
Oracle `IDENTITY` vs Aurora PostgreSQL `SERIAL` syntax differs significantly but auto-converts.
- 5574 — No sequence statuses.

### Views — ★★★★ (High)
Basic `CREATE VIEW` syntax nearly identical; some sub-options differ and add manual tasks.
- 5075 — No `WITH READ ONLY` clause for views.
- 5077 — No `PIVOT` clause for `SELECT`.
- 5245 — No views with nested table columns.
- 5320 — No views with `INVALID` status.
- 5321 — No object views.
- 5322 — No typed views.
- 5583 — No constraints for views.
- 5614 — No DML operations with non-updatable views.

### User-defined types — ★★★ (Medium)
UDTs aren't supported; SCT replaces standard UDTs with base types. Complex UDTs may need manual work.
- 5032 — Can't convert UDTs with incomplete definitions.
- 5062 — Converted %s type constructor to a direct assignment.
- 5099 — Can't convert object because parent object %s wasn't created.
- 5118 — No associative arrays.
- 5120 — No collection data type constructors.
- 5121 — No `FORALL` statements.
- 5332 — Can't convert object referencing an unconverted object in schema %s.
- 5569 — Only standard SQL date/time types for session variables.
- 5575 — No `DEFAULT` assignment when creating UDT %s.
- 5577 — No member functions in UDTs.
- 5582 — No encrypted objects in `CREATE`.
- 5587 — No `EXTEND` methods with parameters.
- 5638 — No global variables of nested table as a function/procedure argument.

### Merge — No automation
`MERGE` is unsupported and not auto-converted; manual conversion is straightforward in most cases.
- 5102 — No `MERGE` statements.
- 5618 — No `MERGE` with `ERROR LOG` clause.
- 5621 — Ensure the unique constraint for the %s field exists.

### Materialized views — ★★ (Low)
Materialized views aren't fully supported; incremental refresh and DML on matviews are unsupported.
- 5093 — Can't convert the matview query.
- 5094 — Can't convert the matview.
- 5095 — No DML on materialized views.

### Query hints — ★★★ (Medium)
Basic hints (e.g., index hints) auto-convert except for DML. Oracle optimizations may be inapplicable; start testing with all hints removed, apply selectively as a last resort. Plan guides unsupported.
- 5103 — Can't convert hint %s.

### Database links — No automation
Requires a full rewrite of the database-link mechanism; not auto-converted.
- 5605 — No usage of database links.
- 5639 — Ensure the `postgres_fdw` extension is installed.
- 5640 — Can't convert link because remote table isn't defined (structure created from references).
- 5641 — `postgres_fdw` doesn't support user-defined functions.
- 5657 — Can't create views based on undefined foreign tables.

### Indexes — ★★★★ (High)
Basic non-clustered indexes auto-migrate. Filtered indexes, included-column indexes, and Oracle-specific options (bitmap, domain) need manual conversion.
- 5206 — No bitmap indexes.
- 5208 — No domain indexes.
- 5555 — No multi-column functional indexes.

### Partitioning — ★★★ (Medium)
Aurora PostgreSQL uses table inheritance; physical Oracle concepts (file groups) don't apply. PostgreSQL supports a richer framework (hash partitioning, sub-partitioning).
- 5652 — No mechanism to handle null values for partition keys.
- 5653 — No foreign keys referencing partitioned tables.
- 5654 — No foreign keys in partitioned tables referencing other tables.
- 5655 — Can't convert update operations of partitioned tables/partitions/subpartitions.
- 5656 — Timestamp data type in converted code may produce different results.
- 5658 — `DEFAULT` partitions available in PostgreSQL 11+.

### OLAP functions — ★★★★ (High)
Aurora PostgreSQL natively supports almost all OLAP functions.
- 5271 — `GREATEST` may produce different results.
- 5272 — `LEAST` may produce different results.
- 5622 — Converts `dbms_transaction.local_transaction_id` with the parameter set to true.

## Conversion notes
- Star ratings let you triage effort: ★★★★★/★★★★ topics are mostly mechanical; ★★/★ and "No automation" (Merge, Database links) topics require redesign or full rewrite.
- "No automation" topics in this Oracle→Aurora PostgreSQL set: **Merge** and **Database links**.
- Lowest automation feature with partial support: **Materialized views** (★★).
- Date/time and timestamp handling repeatedly flagged (5213, 5552/5553, 5656, 5584) — verify and test all temporal logic manually.
- `ROWID`/`UROWID`, `BFILE`, nested tables, object types, synonyms, and autonomous transactions have no PostgreSQL equivalent and require redesign.
- For database links, install and use the `postgres_fdw` extension as the replacement mechanism.
