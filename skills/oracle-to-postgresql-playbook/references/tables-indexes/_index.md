# Tables and Indexes — Reference Index

Oracle → Aurora PostgreSQL conversion references distilled from the AWS Oracle→Aurora PostgreSQL Migration Playbook.

## Tables
- [case-sensitivity.md](case-sensitivity.md) — Oracle names are case-insensitive; PostgreSQL folds unquoted names to lower-case and is case-sensitive (use lower-case via DMS transforms).
- [common-data-types.md](common-data-types.md) — Oracle↔PostgreSQL data type mapping tables, BYTE/CHAR semantics, and AWS SCT example; BFILE/ROWID/UROWID need manual handling.
- [read-only-tables-and-replicas.md](read-only-tables-and-replicas.md) — Oracle READ ONLY tables/partitions vs PostgreSQL workarounds (read-only role, database, or trigger).
- [table-constraints.md](table-constraints.md) — PK/FK/UNIQUE/CHECK/NOT NULL mapping; PostgreSQL adds ON UPDATE and EXCLUDE, drops REF and view constraints.
- [temporary-tables.md](temporary-tables.md) — Oracle GLOBAL temp tables vs PostgreSQL session-local temp tables; reversed ON COMMIT default.
- [triggers.md](triggers.md) — Oracle inline-body triggers vs PostgreSQL function+trigger model; no system/DB-event triggers in PostgreSQL.
- [tablespaces-and-data-files.md](tablespaces-and-data-files.md) — Tablespace/data-file concepts; Aurora auto-manages files under /rdsdbdata/tablespaces/.
- [user-defined-types.md](user-defined-types.md) — Oracle OBJECT types vs PostgreSQL composite/enum/range/array types; no AS OBJECT or CREATE OR REPLACE TYPE.
- [unused-columns-and-alter-table.md](unused-columns-and-alter-table.md) — Oracle SET UNUSED/DROP UNUSED vs PostgreSQL DROP COLUMN + VACUUM FULL.
- [virtual-columns.md](virtual-columns.md) — Oracle virtual columns vs PostgreSQL 12+ generated columns, or views/functions/triggers + expression indexes.

## Indexes
- [indexes-summary.md](indexes-summary.md) — Overall index type/feature mapping and CREATE/ALTER/REINDEX DDL equivalents.
- [btree-indexes.md](btree-indexes.md) — B-tree indexes; direct 1:1 conversion (default in both).
- [bitmap-indexes.md](bitmap-indexes.md) — Oracle bitmap indexes have no PostgreSQL equivalent; consider BRIN.
- [composite-multicolumn-indexes.md](composite-multicolumn-indexes.md) — Composite/multicolumn indexes; identical syntax, up to 32 columns.
- [function-based-expression-indexes.md](function-based-expression-indexes.md) — Oracle function-based → PostgreSQL expression indexes (single-column only); plus partial indexes.
- [invisible-indexes.md](invisible-indexes.md) — Oracle invisible indexes; no equivalent in Aurora PostgreSQL.
- [index-organized-and-cluster-tables.md](index-organized-and-cluster-tables.md) — Oracle IOT vs PostgreSQL CLUSTER (one-time, non-persistent sort).
- [partitioned-indexes.md](partitioned-indexes.md) — Oracle local/global partitioned indexes vs PostgreSQL per-partition indexes (no global index).
- [automatic-indexing.md](automatic-indexing.md) — Oracle 19c auto indexing; no Aurora equivalent (Dexter/HypoPG unsupported), diagnostic queries provided.
