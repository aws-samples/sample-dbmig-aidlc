# AWS SCT Action Code Index

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tools.actioncode.html

**Conversion category:** N/A (tooling)
**SCT automation:** This page is the master index of SCT automation levels and action codes for SQL Server → Aurora PostgreSQL.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): added a status table of action codes obsolete on PG 18 (MERGE, WITH TIES, INCLUDE, FKs on partitioned tables, PostGIS, ltree, procedures with COMMIT/OUT, generated columns, pg_cron; verified) and the list that still needs manual work; corrected SET DEFAULT and Apache AGE notes.

## SQL Server
- Source-side T-SQL/schema features that AWS SCT analyzes during conversion. Each feature is rated by automation level and emits specific action codes for items needing manual attention.

## PostgreSQL
- Target-side equivalents and limitations. Action messages describe what PostgreSQL doesn't support and how SCT handles (skips/replaces) each construct.

## Action codes that no longer describe a limitation on Aurora PostgreSQL 18

SCT/DMS SC still emit many of the codes below, but several reflect PostgreSQL 10-era limits. When triaging output for a PG 18 target, treat these as **"convert natively"** (verified on 18.6 unless marked):

| Code(s) | Original meaning | Status on Aurora PostgreSQL 18 |
|---|---|---|
| 7915, 7916 | No `MERGE` | Native `MERGE` (PG 15) + `RETURNING`/`NOT MATCHED BY SOURCE` (PG 17). See `../tsql/merge.md` |
| 7605 | No `TOP … WITH TIES` | `FETCH FIRST n ROWS WITH TIES` (PG 13+, verified) |
| 7682 | No `INCLUDE` in indexes | Supported (PG 11+) |
| 7606, 7911 | No FKs referencing partitioned tables | Supported (PG 12+, verified) |
| 7912 | No FKs from partitioned tables | Supported (PG 11+) |
| 7910 | No NULL partition keys | NULLs go to the `DEFAULT` partition or a list partition `FOR VALUES IN (NULL)` (verified) |
| 7662, 7664 | No `geography`/`geometry` | PostGIS 3.6 on Aurora 18 (verified) |
| 7657 | No `hierarchyid` | `ltree` (available, verified) |
| 7905, 7906 | No `PIVOT`/`UNPIVOT` | `tablefunc` `crosstab()` or `FILTER` aggregation; `UNPIVOT` → `CROSS JOIN LATERAL (VALUES …)` (see `../tsql/pivot-unpivot.md`) |
| 7807 | No transaction control in functions | Use `CREATE PROCEDURE` (PG 11+), which can `COMMIT`/`ROLLBACK` (verified) |
| 7800, 7641–7643 | No SQL Server-style result sets | `RETURNS TABLE`/`SETOF` functions, or `INOUT refcursor` from procedures |
| 7634-style `OUT`/`RETURN` | | Procedures return `INOUT`/`OUT` via `CALL` (PG 14+, verified) |
| 7678, 7679 | Computed columns replaced by regular columns/triggers | Use generated columns: PG 18 `VIRTUAL` (default) or `STORED` |
| 7690 | No table types | Composite types / arrays of composites; table-valued parameters → arrays or temp tables |
| 7646 | Collations not converted | Map deliberately: ICU nondeterministic collations (PG 18 `LIKE` support) / `citext` |
| 7913 | No `RANGE LEFT` | Still no `LEFT`; rewrite boundaries (see `../physical-storage/partitioning.md`) |
| 7902 | No SQL Server Agent | `pg_cron` (available on Aurora 18, verified) / EventBridge Scheduler |

Codes that **still** mean manual work on PG 18 include 7809 (`INSTEAD OF` triggers on tables), 7628 (`GOTO`), 7691/7821 (`WAITFOR TIME`; `pg_sleep` covers `WAITFOR DELAY` only), 7637/7639/7700/7704 (global/dynamic/keyset cursors), 7658 (`sql_variant`), 7665/7835 (FILESTREAM/FileTable), 7688 (full-text predicates), 7792 (synonyms), 7816/7817/7920 (XML methods / `FOR XML`), 7645 (pass-through to linked servers, partly covered by `dblink`), 7900/7901/7903 (Database Mail, Service Broker, `BACKUP`), and 7931/7932 (SQL Graph; Apache AGE is **not** available on Aurora 18).

## Automation level legend
- **Full automation (5★)** — fully automatic, no manual conversion.
- **High automation (4★)** — minor, simple manual conversions may be needed.
- **Medium automation (3★)** — low–medium complexity manual conversions may be needed.
- **Low automation (2★)** — medium–high complexity manual conversions may be needed.
- **Very low automation (1★)** — high risk or complex manual conversions may be needed.
- **No automation** — not supported by AWS SCT; manual conversion required.

## Conversion notes

### Creating Tables — High (4★)
Auto-converts most `CREATE TABLE` constructs (ANSI entry-level): table/column names, schema, basic data types, column/table constraints, defaults, primary/UNIQUE/foreign keys. Computed columns and global temp tables may need changes.
- `7659` — If you use recursion, ensure table variables (source) and temp tables (target) have the same scope.
- `7665` — PostgreSQL doesn't support `FILESTREAM` clauses; SCT skips them.
- `7678` — SCT replaced computed columns with regular columns.
- `7679` — SCT replaced computed columns with triggers.
- `7680` — PostgreSQL doesn't support global temporary tables.
- `7812` — Remove the temporary table before the end of the function.
- `7835` — PostgreSQL doesn't support `CREATE TABLE ... AS FileTable`.

### Data Types — High (4★)
Most types convert automatically. Date/time paradigms differ — require manual verification. Strict testing recommended due to behavior differences.
- `7657` — PostgreSQL doesn't support the `hierarchyid` data type.
- `7658` — PostgreSQL doesn't support the `sql_variant` data type.
- `7662` — PostgreSQL doesn't support the `geography` data type.
- `7664` — PostgreSQL doesn't support the `geometry` data type.
- `7690` — PostgreSQL doesn't support table types.
- `7706` — SCT can't convert the declaration of a variable of the unsupported %s data type.
- `7707` — SCT can't convert the usage of a variable of the unsupported %s data type.
- `7708` — SCT can't convert the usage of the unsupported %s data type.
- `7773` — SCT can't convert arithmetic operations with dates.
- `7775` — Converted code might lose accuracy compared to source.

### Collations — No automation
Collation paradigms differ significantly; SCT can't migrate collations automatically.
- `7646` — AWS SCT can't convert collations.

### PIVOT and UNPIVOT — No automation
(Original wording.) PostgreSQL has no `PIVOT`/`UNPIVOT` keywords even in PG 18; see the status table for the rewrites.
- `7905` — PostgreSQL doesn't support `PIVOT` clauses for `SELECT` statements.
- `7906` — PostgreSQL doesn't support `UNPIVOT` clauses for `SELECT` statements.

### TOP and FETCH — High (4★)
Aurora PostgreSQL supports `LIMIT … OFFSET` for paging. `WITH TIES` and some options need manual conversion.
- `7605` — PostgreSQL doesn't support the `WITH TIES` argument in `TOP` clauses.
- `7796` — PostgreSQL doesn't support `TOP` clauses in `UPDATE` statements.
- `7798` — PostgreSQL doesn't support `TOP` clauses in `DELETE` statements.
- `7799` — PostgreSQL doesn't support `TOP` clauses in `INSERT` operators.

### Cursors — Medium (3★)
PL/pgSQL cursors (always `refcursor`) iterate query results. Some options unsupported.
- `7637` — PostgreSQL doesn't support global cursors.
- `7639` — PostgreSQL doesn't support dynamic cursors.
- `7700` — Can't convert the `KEYSET` option (PostgreSQL can't change cursor row membership/order).
- `7701` — Doesn't convert `FAST_FORWARD` (default in PostgreSQL).
- `7702` — Doesn't convert `READ_ONLY` (default in PostgreSQL).
- `7704` — PostgreSQL doesn't support the `OPTIMISTIC` option for cursors.
- `7705` — PostgreSQL doesn't support the `TYPE_WARNING` option for cursors.
- `7803` — PostgreSQL doesn't support the `FOR UPDATE` option.

### Flow Control — Medium (3★)
Most constructs (loops, command blocks, delays) convert. `GOTO` and `WAITFOR TIME` unsupported.
- `7628` — PostgreSQL doesn't support `GOTO` statements.
- `7691` — PostgreSQL doesn't support the `WAITFOR TIME` feature.
- `7801` — Ensure your table isn't locked by an open cursor.
- `7802` — Delete the table you created within the procedure before the end of the procedure.
- `7810` — PostgreSQL doesn't support `SET NOCOUNT OFF` statements.
- `7821` — SCT can't convert the `WAITFOR` operator with a variable.
- `7826` — SCT can't convert the default value of the `DateTime` variable.
- `7827` — SCT can't convert default values.

### Transaction Isolation — Medium (3★)
Supports the four SQL:92 isolation levels (`READ UNCOMMITTED`, `READ COMMITTED`, `REPEATABLE READ`, `SERIALIZABLE`); converts `BEGIN/COMMIT/ROLLBACK`. Named/marked/delayed-durability transactions need manual conversion.
- `7807` — Can't convert the transaction management command. PostgreSQL doesn't support explicit transaction management (`BEGIN TRAN`, `SAVE TRAN`) in functions.

### Stored Procedures — High (4★)
Similar functionality; auto-converted. `RETURN` values and some `EXECUTE` options (`RECOMPILE`, `RESULT SETS`) need manual conversion.
- `7640` — PostgreSQL doesn't support `EXECUTE` with the `WITH RECOMPILE` option.
- `7641` — PostgreSQL doesn't support `EXECUTE` with `RESULT SETS UNDEFINED`.
- `7642` — PostgreSQL doesn't support `EXECUTE` with `RESULT SETS NONE`.
- `7643` — PostgreSQL doesn't support `EXECUTE` with `RESULT SETS DEFINITION`.
- `7672` — PostgreSQL doesn't support `EXECUTE` statements that run a character string.
- `7695` — PostgreSQL doesn't support the call of a procedure as a variable.
- `7800` — PostgreSQL doesn't support result sets in the SQL Server style.
- `7830` — SCT can't convert arithmetic operations with the `CASE` operand.
- `7838` — SCT can't convert `EXECUTE` statements with `LOGIN` or `USER` options.
- `7839` — Converted code might not work correctly because of parameter names.

### Triggers — Medium (3★)
Supports `BEFORE`/`AFTER` triggers for `INSERT`/`UPDATE`/`DELETE`, but differs substantially from SQL Server.
- `7809` — PostgreSQL doesn't support `INSTEAD OF` triggers on tables.
- `7832` — SCT can't convert `INSTEAD OF` triggers on views.
- `7909` — SCT can't convert `UPDATE(column)` or `COLUMNS_UPDATED` statements.

### MERGE — No automation (in the original playbook)
Aurora PostgreSQL 10 had no `MERGE`; PG 15+ does (see the status table).
- `7915` — Converted code might produce different results. Ensure the constraint includes the %s column.
- `7916` — SCT can't emulate `MERGE` using the `INSERT ON CONFLICT` statement.

### Query Hints — Medium (3★)
Can convert basic query hints (e.g. index hints) except for DML. Plan guides unsupported. Recommendation: start testing with all hints removed, apply selectively as last resort.
- `7823` — PostgreSQL doesn't support table hints in DML statements.

### Full-Text Search — No automation
Requires full rewrite of code that creates/manages/queries full-text indexes.
- `7688` — PostgreSQL doesn't support `FREETEXT` predicates.

### Indexes — Medium (3★)
Basic non-clustered indexes auto-migrated. Filtered indexes, included columns, and SQL Server-specific options need manual conversion.
- `7675` — PostgreSQL doesn't support `ASC`/`DESC` sorting options for constraints.
- `7681` — PostgreSQL doesn't support clustered indexes.
- `7682` — PostgreSQL doesn't support the `INCLUDE` option in indexes.
- `7781` — PostgreSQL doesn't support the `PAD_INDEX` option.
- `7782` — PostgreSQL doesn't support the `SORT_IN_TEMPDB` option.
- `7783` — PostgreSQL doesn't support the `IGNORE_DUP_KEY` option.
- `7784` — PostgreSQL doesn't support the `STATISTICS_NORECOMPUTE` option.
- `7785` — PostgreSQL doesn't support the `STATISTICS_INCREMENTAL` option.
- `7786` — PostgreSQL doesn't support the `DROP_EXISTING` option.
- `7787` — PostgreSQL doesn't support the `ONLINE` option.
- `7788` — PostgreSQL doesn't support the `ALLOW_ROW_LOCKS` option.
- `7789` — PostgreSQL doesn't support the `ALLOW_PAGE_LOCKS` option.
- `7790` — PostgreSQL doesn't support the `MAXDOP` option.
- `7791` — PostgreSQL doesn't support the `DATA_COMPRESSION` option.

### Partitioning — Medium (3★)
(Original wording; current Aurora PostgreSQL uses declarative partitioning, not inheritance.) SQL Server physical aspects (file groups) don't apply. PostgreSQL offers richer partitioning (hash, sub-partitioning).
- `7910` — PostgreSQL doesn't support `NULL` columns for partitioning. *(From PostgreSQL 11+, NULL columns for partitioning are supported — you can ignore 7910 and use NULL columns.)*
- `7911` — PostgreSQL doesn't support foreign keys referencing partitioned tables.
- `7912` — PostgreSQL doesn't support foreign key references from partitioned tables to other tables.
- `7913` — PostgreSQL doesn't support `LEFT` partitioning.
- `7914` — Converted code might produce different results compared to source.

### Backup — No automation
Paradigm shift to PaaS; Amazon RDS provides continuous backup with point-in-time restore up to 35 days.
- `7903` — PostgreSQL doesn't support functionality similar to SQL Server Backup.

### SQL Server Mail — No automation
Aurora PostgreSQL has no native email-from-database support.
- `7900` — PostgreSQL doesn't support functionality similar to SQL Server Database Mail.

### Graph — No automation
SCT doesn't convert graph database capabilities. The Apache AGE extension mentioned by the playbook is **not** available on Aurora PostgreSQL 18 (checked 18.6); use recursive CTEs over edge tables, or Amazon Neptune.
- `7931` — SCT can't convert SQL Graph tables.
- `7932` — SCT can't convert DML constructs of SQL Graph databases.

### SQL Server Agent — No automation
No external cross-instance scheduler equivalent; Aurora PostgreSQL has `pg_cron` as an in-database scheduler (verified on 18.6).
- `7902` — PostgreSQL doesn't support functionality similar to SQL Server Agent.

### Service Broker — No automation
No compatible solution; use DB Links + AWS Lambda for similar functionality.
- `7901` — PostgreSQL doesn't support functionality similar to SQL Server Service Broker.

### XML — Medium (3★)
XML options similar to SQL Server `XPATH`/`XQUERY`. No `FOR XML` clause — use `string_agg` instead; JSON may be more efficient.
- `7816` — PostgreSQL doesn't support methods for the XML data type.
- `7817` — PostgreSQL doesn't support the `FOR XML PATH` option in SQL queries.
- `7920` — PostgreSQL doesn't support `EXPLICIT` mode with `FOR XML`.
- `7924` — PostgreSQL doesn't support XPath queries that return multiple elements.

### Constraints — High (4★)
Almost fully automated/compatible. Difference: check constraints with sub-queries. (`SET DEFAULT` **is** supported in PostgreSQL, verified; the original "missing `SET DEFAULT`" note is wrong.)
- `7606` — PostgreSQL doesn't support foreign keys that reference partitioned tables.
- `7675` — PostgreSQL doesn't support `ASC`/`DESC` sorting options for constraints.
- `7825` — SCT removed the default value of the `DateTime` column.
- `7915` — Converted code might produce different results. Ensure the constraint includes the %s column.

### Linked Servers — Medium (3★)
Supports remote data access; cross-schema is trivial, cross-instance requires an extension.
- `7645` — PostgreSQL doesn't support running pass-through commands on linked servers.

### Synonyms — Medium (3★)
Supports synonyms; replace table/view/function synonyms with views or wrapper functions. More challenging for other object types.
- `7792` — PostgreSQL doesn't support synonyms.
