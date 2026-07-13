# ANSI SQL — Reference Index

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> Chapter: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.html

Distilled reference files for the "Migrating ANSI SQL features" chapter (SQL Server 2019 →
Amazon Aurora MySQL).

| File | Topic | Conversion category |
|---|---|---|
| [ansi-sql.md](ansi-sql.md) | Chapter overview | N/A |
| [case-sensitivity.md](case-sensitivity.md) | Case sensitivity differences | Assisted |
| [constraints.md](constraints.md) | Constraints (CHECK, UNIQUE, PK, FK) | Assisted |
| [creating-tables.md](creating-tables.md) | Creating tables | Assisted |
| [cte.md](cte.md) | Common table expressions | Manual |
| [data-types.md](data-types.md) | Data types | Assisted |
| [group-by.md](group-by.md) | GROUP BY | Assisted |
| [table-join.md](table-join.md) | Table JOIN | Assisted |
| [views.md](views.md) | Views | Assisted |
| [window-functions.md](window-functions.md) | Window functions | Manual |
| [temporary-tables.md](temporary-tables.md) | Temporary tables | Assisted |

## Key migration themes
- **Not supported in Aurora MySQL:** `CHECK` constraints (parsed but ignored), `FULL OUTER JOIN`, `CROSS/OUTER APPLY`, indexed/partitioned/temporary views, triggers on views, global temp tables, table variables, memory-optimized tables, `MONEY`, `UNIQUEIDENTIFIER`, `HIERARCHYID`, `XML`, `SQL_VARIANT`, `TABLE` type.
- **5.7-version gaps (available in MySQL 8):** Common Table Expressions and Window functions — rewrite using derived tables, stored-procedure loops, or correlated subqueries.
- **Syntax swaps:** `IDENTITY` → `AUTO_INCREMENT`, `SELECT INTO` → `CREATE TABLE … AS`, `#TempTable` → `CREATE TEMPORARY TABLE`, `STRING_AGG` → `GROUP_CONCAT`, `STDEVP` → `STDDEV_POP`.
- **Behavioral differences:** case sensitivity via `lower_case_table_names`, PKs always clustered, FKs may reference non-unique parent columns, out-of-range values clipped unless STRICT mode.
