# Physical Storage — Reference Index

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> Chapter URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.storage.html

The Storage chapter of the playbook is a single content page covering table/index
partitioning. It has no `chap-sql-server-aurora-mysql.storage.<sub>.html` subpages —
only in-page anchors (SQL Server Usage, MySQL Usage, Summary). Its content is captured
in a single reference file.

| File | Topic | Conversion category | SCT automation |
|---|---|---|---|
| [storage.md](storage.md) | Partitioning (table/index partitioning) | Manual (three-star, no automation) | N/A — action code: Partitioning |

## Key takeaways

- SQL Server: all tables partitioned; `RANGE` only; partition function + partition
  scheme (file groups); `LEFT`/`RIGHT` boundaries; partition-to-partition switching.
- Aurora MySQL: explicit partitioning only; `RANGE`, `LIST`, `HASH`, `KEY` +
  subpartitioning; `RIGHT` boundaries only; physical storage managed by RDS (no
  partition scheme/file groups); exchange only with a non-partitioned table.
- Aurora MySQL restrictions: no foreign keys, no `FULLTEXT`, no spatial types on
  partitioned tables; partitioning keys must be `INT` (with exceptions for COLUMNS and
  `[LINEAR] KEY` partitioning).
