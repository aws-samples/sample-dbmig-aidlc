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
> **Target baseline: Aurora PostgreSQL 18** (validated on 18.6). Highlights: `ON DELETE SET DEFAULT` **is** supported; SQL Server single-NULL UNIQUE → `UNIQUE NULLS NOT DISTINCT`; computed columns → PG 18 `VIRTUAL`/`STORED` generated columns; `IDENTITY` → identity (not `SERIAL`); `NOCHECK` constraints → `NOT VALID`/`NOT ENFORCED`; case-insensitive data → nondeterministic ICU collation (PG 18 `LIKE` support) or `citext`; `AVG(int)` returns numeric. See `../target-baseline-aurora-postgresql-18.md`.

- **High-effort / manual:** Temporal tables (no system versioning on Aurora — rebuild with a history table + trigger; PG 18 `WITHOUT OVERLAPS` helps for application-time periods).
- **Watch-outs requiring rewrite:**
  - Subqueries in check constraints; UNIQUE single-NULL semantics (constraints). (`SET DEFAULT` is supported.)
  - `IDENTITY`→`GENERATED … AS IDENTITY`, `ON <File Group>`, table variables, `##` global temp tables, memory-optimized tables, `ROWVERSION` (creating tables).
  - `TINYINT`/`SMALLMONEY`/`BINARY`/`UNIQUEIDENTIFIER`/`HIERARCHYID`/`SQL_VARIANT`/`ROWVERSION` type mappings (data types).
  - `OUTER JOIN` with commas (`*=`/`=*`), `CROSS APPLY`/`OUTER APPLY` → `LATERAL` joins (table join).
  - `WITH CUBE`/`WITH ROLLUP`/`GROUP BY ALL` legacy syntax (group by).
  - Indexed and partitioned views (views).
  - `RECURSIVE` keyword required, `MAXRECURSION`, `AVG(int)` type difference (CTEs, GROUP BY).
- **Mostly seamless:** Derived tables, window functions, basic GROUP BY — syntax largely identical (verify returned data types).
