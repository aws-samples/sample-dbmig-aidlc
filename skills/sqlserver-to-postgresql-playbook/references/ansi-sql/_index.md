# ANSI SQL — SQL Server → Aurora PostgreSQL Reference Index

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> Base URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/

Distilled reference notes for the ANSI SQL section of the AWS SQL Server 2019 → Amazon Aurora PostgreSQL Migration Playbook. Each file preserves the playbook's SQL examples and comparison tables.

| Topic | File | Conversion category | SCT automation |
|---|---|---|---|
| Case Sensitivity | [case-sensitivity.md](case-sensitivity.md) | Assisted | SCT lowercases names; DMS transformation rules |
| Constraints | [constraints.md](constraints.md) | Automatic (★★★★★ / ★★★★) | High — action code: Constraints |
| Creating Tables | [creating-tables.md](creating-tables.md) | Assisted (★★★ / ★★★★) | Action code: Creating Tables |
| Common Table Expressions | [common-table-expressions.md](common-table-expressions.md) | Automatic (★★★★★ / ★★★★★) | N/A |
| Data Types | [data-types.md](data-types.md) | Assisted (★★★★ / ★★★★) | Action code: Data Types |
| Derived Tables | [derived-tables.md](derived-tables.md) | Automatic (★★★★★ / ★★★★★) | N/A |
| GROUP BY | [group-by.md](group-by.md) | Automatic (★★★★★ / ★★★★★) | N/A |
| Table JOIN | [table-join.md](table-join.md) | Assisted (★★★★ / ★★★★) | N/A |
| Temporal Tables | [temporal-tables.md](temporal-tables.md) | Manual (★★ / none) | N/A |
| Views | [views.md](views.md) | Assisted (★★★★ / ★★★★) | N/A |
| Window Functions | [window-functions.md](window-functions.md) | Automatic (★★★★★ / ★★★★★) | N/A |

## Key migration takeaways
- **High-effort / manual:** Temporal tables (no Aurora support — rebuild with triggers + custom history table).
- **Watch-outs requiring rewrite:**
  - `SET DEFAULT` referential action, subqueries in check constraints (constraints).
  - `IDENTITY`→`SERIAL`, `ON <File Group>`, table variables, memory-optimized tables, `ROWVERSION` (creating tables).
  - `TINYINT`/`SMALLMONEY`/`BINARY`/`UNIQUEIDENTIFIER`/`HIERARCHYID`/`SQL_VARIANT`/`ROWVERSION` type mappings (data types).
  - `OUTER JOIN` with commas (`*=`/`=*`), `CROSS APPLY`/`OUTER APPLY` → `LATERAL` joins (table join).
  - `WITH CUBE`/`WITH ROLLUP`/`GROUP BY ALL` legacy syntax (group by).
  - Indexed and partitioned views (views).
  - `RECURSIVE` keyword required + integer division casting (CTEs).
- **Mostly seamless:** Derived tables, window functions, basic GROUP BY — syntax largely identical (verify returned data types).
