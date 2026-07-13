# Physical Storage — SQL Server → Aurora PostgreSQL

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> Reference set distilled from the "Physical storage" chapter.

Reference files comparing SQL Server 2019 physical-storage features against Amazon Aurora PostgreSQL.

| Topic | File | Conversion category | SCT automation |
|---|---|---|---|
| Columnstore index functionality | [columnstore-indexes.md](columnstore-indexes.md) | Manual (no feature compatibility) | N/A |
| Indexed / materialized view functionality | [indexed-and-materialized-views.md](indexed-and-materialized-views.md) | Manual (two-star compatibility) | N/A |
| Partitioning databases | [partitioning.md](partitioning.md) | Assisted (two-star compatibility, three-star automation) | Partitioning |

## Key takeaways

- **Columnstore indexes** have no Aurora PostgreSQL equivalent — manual redesign required (partitioning, BRIN indexes, or a columnar system such as Amazon Redshift for analytics).
- **Indexed views** map to PostgreSQL **materialized views**, but lose automatic refresh and DML support; refresh is manual or trigger-driven and full-only.
- **Partitioning** is broadly supported via declarative partitioning (PostgreSQL 10+), but note PostgreSQL has no `LEFT` boundary, no `EXCHANGE`/`SPLIT`, and no foreign keys referencing partitioned tables.
