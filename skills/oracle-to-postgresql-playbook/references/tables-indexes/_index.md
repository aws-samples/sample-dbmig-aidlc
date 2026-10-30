# Tables and Indexes — Reference Index

> **Target baseline: Aurora PostgreSQL 18** (validated on 18.6). Schema defaults: `NUMBER` → `numeric` (per `datatype-map.yaml`); identity over `SERIAL`; virtual columns → `GENERATED … VIRTUAL` (use `STORED` if indexed/unique/FK/UDF); drop `TABLESPACE` clauses; `DISABLE NOVALIDATE` → `NOT ENFORCED`; bitmap → B-tree; identifiers ≤ 63 bytes. Full list: `../target-baseline-aurora-postgresql-18.md`.

Oracle → Aurora PostgreSQL conversion references distilled from the AWS Oracle→Aurora PostgreSQL Migration Playbook.

## Tables
- [case-sensitivity.md](case-sensitivity.md) — Oracle names are case-insensitive; PostgreSQL folds unquoted names to lower-case and is case-sensitive (use lower-case via DMS transforms); 63-byte silent truncation.
- [common-data-types.md](common-data-types.md) — Oracle↔PostgreSQL data type mapping (toolkit `datatype-map.yaml` wins: `NUMBER` → `numeric`), BYTE/CHAR semantics, AWS SCT example; BFILE/ROWID/UROWID need manual handling; pgvector/PostGIS for VECTOR/SDO.
- [read-only-tables-and-replicas.md](read-only-tables-and-replicas.md) — Oracle READ ONLY tables/partitions vs PostgreSQL workarounds (read-only role, database, or trigger).
- [table-constraints.md](table-constraints.md) — PK/FK/UNIQUE/CHECK/NOT NULL mapping; PG 18 `NOT ENFORCED` (≈ DISABLE NOVALIDATE), named NOT NULL, temporal keys; composite-UNIQUE NULL difference; no REF or view constraints.
- [temporary-tables.md](temporary-tables.md) — Oracle GLOBAL temp tables vs PostgreSQL session-local temp tables (`GLOBAL` ignored); reversed ON COMMIT default; GTT conversion patterns.
- [triggers.md](triggers.md) — Oracle inline-body triggers vs PostgreSQL function+trigger model; `login` event trigger (PG 17) for LOGON; alphabetical firing order; no STARTUP/SHUTDOWN/SERVERERROR triggers.
- [tablespaces-and-data-files.md](tablespaces-and-data-files.md) — Tablespace/data-file concepts; on Aurora tablespaces are logical only, so drop TABLESPACE clauses by default.
- [user-defined-types.md](user-defined-types.md) — Oracle OBJECT types vs PostgreSQL composite/enum/range/array types; no AS OBJECT or CREATE OR REPLACE TYPE; constructor calls become `ROW(...)` and attribute access needs parentheses `(col).attr`. **Create types before anything referencing them.** Automatic for the DDL — but **collection use inside PL/SQL is Manual**, see `../sql-plsql/collections-and-bulk-operations.md`.
- [unused-columns-and-alter-table.md](unused-columns-and-alter-table.md) — Oracle SET UNUSED/DROP UNUSED vs PostgreSQL DROP COLUMN + VACUUM FULL / `pg_repack`; instant `ADD COLUMN … DEFAULT`.
- [virtual-columns.md](virtual-columns.md) — Oracle virtual columns vs PostgreSQL 18 `VIRTUAL` (default) / `STORED` generated columns; virtual columns cannot be indexed, unique, FK targets or use UDFs.

## Indexes
- [indexes-summary.md](indexes-summary.md) — Overall index type/feature mapping and CREATE/ALTER/REINDEX DDL equivalents.
- [btree-indexes.md](btree-indexes.md) — B-tree indexes; direct 1:1 conversion (default in both).
- [bitmap-indexes.md](bitmap-indexes.md) — Oracle bitmap indexes have no PostgreSQL equivalent; default to B-tree (deduplication, PG 18 skip scan), partial, `bloom` or BRIN.
- [composite-multicolumn-indexes.md](composite-multicolumn-indexes.md) — Composite/multicolumn indexes; identical syntax, up to 32 columns; PG 18 skip scan.
- [function-based-expression-indexes.md](function-based-expression-indexes.md) — Oracle function-based → PostgreSQL expression indexes (multi-expression supported; functions must be IMMUTABLE); plus partial indexes.
- [invisible-indexes.md](invisible-indexes.md) — Oracle invisible indexes; no equivalent, but HypoPG (available on Aurora 18) and `pg_hint_plan` cover the what-if use cases.
- [index-organized-and-cluster-tables.md](index-organized-and-cluster-tables.md) — Oracle IOT vs PostgreSQL CLUSTER (one-time) / `pg_repack` / covering `INCLUDE` index.
- [partitioned-indexes.md](partitioned-indexes.md) — Oracle local/global partitioned indexes vs PostgreSQL parent-level (per-partition) indexes; no global index; `ON ONLY` + `ATTACH` for online builds.
- [automatic-indexing.md](automatic-indexing.md) — Oracle 19c auto indexing; no Aurora equivalent, but HypoPG is available on Aurora 18 (Dexter works client-side); diagnostic queries provided.
