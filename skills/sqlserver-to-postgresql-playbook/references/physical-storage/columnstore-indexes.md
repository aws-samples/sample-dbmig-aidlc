# Columnstore Index Functionality

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.storage.columnstore.html

**Conversion category:** Manual (No feature compatibility — Aurora PostgreSQL offers no comparable feature)
**SCT automation:** N/A (No automation)

## SQL Server

SQL Server provides columnstore indexes that use column-based data storage to compress data and improve query performance in data warehouses. Columnstore indexes are the preferred data storage format for data warehousing and analytic workloads. As a best practice, use columnstore indexes with fact tables and large dimension workloads.

```sql
CREATE TABLE products(ID [int] NOT NULL, OrderDate [int] NOT NULL, ShipDate [int] NOT NULL);
GO

CREATE CLUSTERED COLUMNSTORE INDEX cci_T1 ON products;
GO
```

For more information, see [Columnstore indexes: Overview](https://docs.microsoft.com/en-us/sql/relational-databases/indexes/columnstore-indexes-overview?view=sql-server-2017) in the SQL Server documentation.

## PostgreSQL

Amazon Aurora PostgreSQL-Compatible Edition (Aurora PostgreSQL) doesn't currently provide a directly comparable alternative for the SQL Server columnstore index.

## Conversion notes

- There is no equivalent to columnstore indexes in Aurora PostgreSQL — conversion must be handled manually with no SCT/DMS automation.
- Columnstore indexes are an OLAP/data-warehouse optimization (column-oriented storage + compression). Migrating to row-oriented PostgreSQL requires rethinking the storage/query strategy.
- Possible alternatives to consider: standard B-tree/BRIN indexes for large append-only fact tables, table partitioning to limit scan ranges, table compression at the storage layer, or moving analytic workloads to a column-oriented system (e.g., Amazon Redshift) if columnar performance is essential.
- Expect query performance characteristics to differ; validate analytic query plans and timings after migration.
