# Indexes — Reference Index

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.indexes.html

Reference material for migrating B-tree indexes from SQL Server to Aurora MySQL.

| File | Topic | Conversion category |
|---|---|---|
| [indexes.md](indexes.md) | Migrating indexes to Aurora MySQL (clustered/PK, nonclustered/secondary, filtered, covering/included, computed/generated columns, prefix indexes) | Automatic (★★★★) |

## Key takeaways

- Aurora MySQL clusters on the **primary key only** — non-PK clustered indexes have no
  direct equivalent.
- **Filtered indexes** and **included (covering) columns** are not supported; promote
  included columns to index key columns and redesign filtered indexes.
- SQL Server computed columns map to MySQL **STORED** generated columns (only STORED are
  indexable).
- Limits differ: max non-clustered indexes 999 → 64; max columns per index 32 → 16; max
  key size 900 bytes → up to 3072 bytes (16 KB page).
