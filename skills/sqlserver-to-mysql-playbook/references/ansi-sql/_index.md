# ANSI SQL — Reference Index

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> Chapter: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.html

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29). CTEs, window functions, `CHECK`, `LATERAL` and generated columns are native; still missing: `FULL OUTER JOIN`, `GROUPING SETS`/`CUBE`, updatable CTEs, single-NULL unique keys, FKs on temporary tables. Baseline: `../../../oracle-to-mysql-playbook/references/target-baseline-aurora-mysql.md`.

Distilled reference files for the "Migrating ANSI SQL features" chapter (SQL Server 2019 →
Amazon Aurora MySQL).

| File | Topic | Conversion category |
|---|---|---|
| [ansi-sql.md](ansi-sql.md) | Chapter overview | N/A |
| [case-sensitivity.md](case-sensitivity.md) | Case sensitivity differences | Assisted |
| [constraints.md](constraints.md) | Constraints (CHECK, UNIQUE, PK, FK) | Assisted |
| [creating-tables.md](creating-tables.md) | Creating tables | Assisted |
| [cte.md](cte.md) | Common table expressions | Automatic (native on 3 / 8.4) |
| [data-types.md](data-types.md) | Data types | Assisted |
| [group-by.md](group-by.md) | GROUP BY | Assisted |
| [table-join.md](table-join.md) | Table JOIN | Assisted |
| [views.md](views.md) | Views | Assisted |
| [window-functions.md](window-functions.md) | Window functions | Automatic (native on 3 / 8.4) |
| [temporary-tables.md](temporary-tables.md) | Temporary tables | Assisted |

## Key migration themes
- **Not supported in Aurora MySQL:** `FULL OUTER JOIN`, indexed/partitioned/temporary views, triggers on views, global temp tables, table variables, memory-optimized tables, `MONEY`, `UNIQUEIDENTIFIER`, `HIERARCHYID`, `XML`, `SQL_VARIANT`, `TABLE` type.
- **Native on Aurora MySQL 3 / 8.4 (were 5.7 gaps):** CTEs, window functions, `CHECK` constraints (enforced), `CROSS/OUTER APPLY` → `LATERAL`, computed columns. The derived-table/loop/correlated-subquery workarounds are legacy.
- **Syntax swaps:** `IDENTITY` → `AUTO_INCREMENT`, `SELECT INTO` → `CREATE TABLE … AS`, `#TempTable` → `CREATE TEMPORARY TABLE`, `STRING_AGG` → `GROUP_CONCAT`, `STDEVP` → `STDDEV_POP`.
- **Behavioral differences (verified):** table names case-sensitive by default (`lower_case_table_names` = 0, set only at cluster creation); PKs always clustered; unique keys allow many NULLs; FKs to non-unique keys only on 3.x; column-level `REFERENCES` silently ignored; `ON DELETE SET DEFAULT` acts as `RESTRICT`; `#temp` tables can't be referenced twice in one statement (1137) or have FKs; Aurora default `sql_mode` is **empty** (no strict mode: silent truncation and zero dates).
