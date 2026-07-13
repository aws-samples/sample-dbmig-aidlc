# SQL Server Deprecated Features

> **Source:** SQL Server 2018 deprecated features list — Microsoft SQL Server 2019 to Amazon Aurora PostgreSQL Migration Playbook
> **URL:** https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.deprecatedfeatures.html

This page lists SQL Server features that are deprecated in SQL Server and that warrant attention when migrating to Amazon Aurora PostgreSQL. Each item notes the deprecated SQL Server construct and the recommended replacement on Aurora PostgreSQL.

## SQL Server

| Deprecated SQL Server feature | Replacement / Aurora PostgreSQL equivalent |
|---|---|
| `TEXT`, `NTEXT`, and `IMAGE` data types | Use large-object / variable-length types. On Aurora PostgreSQL use `TEXT` (character) and `BYTEA` (binary). See *Data Types*. |
| `SET ROWCOUNT` for DML | Deprecated for `INSERT`, `UPDATE`, and `DELETE`. Use `TOP` / a row-limiting predicate; on Aurora PostgreSQL use `LIMIT`. See *Session Options*. |
| `TIMESTAMP` syntax for `CREATE TABLE` | The SQL Server `TIMESTAMP` (rowversion) column syntax is deprecated. Use `rowversion`; on Aurora PostgreSQL model with a proper timestamp/`bytea` or sequence-based row version. See *Creating Tables*. |
| `DBCC DBREINDEX`, `INDEXDEFRAG`, and `SHOWCONTIG` | Use `ALTER INDEX ... REBUILD/REORGANIZE` and catalog views in SQL Server; on Aurora PostgreSQL use `REINDEX` / `VACUUM` and the autovacuum framework. See *Maintenance Plans*. |
| Old SQL Mail | Use Database Mail in SQL Server; on Aurora PostgreSQL integrate Amazon services (e.g., Lambda / SES) for email. See *Database Mail*. |
| `IDENTITY` seed, increment, non-primary-key, and compound | On Aurora PostgreSQL use `SERIAL` / `IDENTITY` columns and `SEQUENCE` objects (note sequence behavior differs across restarts). See *Sequences and Identity*. |
| Stored procedures `RETURN` values | Use output parameters or result sets; on Aurora PostgreSQL use `CREATE FUNCTION` returning a value (`CREATE PROCEDURE` does not return values the same way). See *Stored Procedures*. |
| `GROUP BY ALL`, `CUBE`, and `COMPUTE BY` | Use ANSI grouping: `GROUP BY`, `GROUPING SETS`, `CUBE`, `ROLLUP`. `COMPUTE BY` has no equivalent — use aggregate queries / window functions. See *GROUP BY*. |
| DTS (Data Transformation Services) | Use SSIS or, for migration, AWS DMS / modern ETL services. See *ETL*. |
| Old outer join syntax `*=` and `=*` | Use ANSI explicit `LEFT OUTER JOIN` / `RIGHT OUTER JOIN` syntax. See *Table JOIN*. |
| `'String Alias' = Expression` | Use the ANSI `Expression AS Alias` syntax. Aurora PostgreSQL treats `'Alias' = Expression` as a logical predicate. See *Migration Quick Tips*. |
| `DEFAULT` keyword for `INSERT` statements | Use explicit column values or rely on column defaults; review `INSERT ... DEFAULT` usage. See *Migration Quick Tips*. |

## Conversion notes

- These constructs are deprecated in SQL Server itself, so encountering them in source code is a signal the code is old and may need broader review during conversion.
- Replace legacy LOB types (`TEXT`/`NTEXT`/`IMAGE`) with `TEXT`/`BYTEA` on Aurora PostgreSQL; behavior and indexing differ from the SQL Server large-object types.
- Convert old-style outer joins (`*=`, `=*`) to ANSI `LEFT/RIGHT OUTER JOIN` — the legacy operators are not supported and can change result semantics.
- Replace alias-by-assignment (`'Alias' = Expression`) with `Expression AS Alias`; the assignment form silently produces a boolean predicate on Aurora PostgreSQL.
- `IDENTITY` → `SERIAL`/`IDENTITY`/sequences: note that Aurora PostgreSQL sequence seed resets relative to the max existing value on restart rather than persisting an in-memory cache. See `../tsql/` for sequence and identity details.
- `RETURN` values from stored procedures map to functions on Aurora PostgreSQL; review the *Stored Procedures* conversion guidance under `../tsql/`.
- `SET ROWCOUNT` → `LIMIT`; `GROUP BY ALL`/`CUBE`/`COMPUTE BY` → ANSI grouping. See `../ansi-sql/` for ANSI-standard SQL conversion details.
