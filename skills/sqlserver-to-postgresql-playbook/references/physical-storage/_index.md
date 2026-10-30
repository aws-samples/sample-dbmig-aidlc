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

- **Columnstore indexes** have no Aurora PostgreSQL equivalent — manual redesign required (partitioning, BRIN indexes, `aurora_analytics` over Parquet/Iceberg in S3 on Aurora 18.6, or a columnar system such as Amazon Redshift / zero-ETL for analytics).
- **Indexed views** map to PostgreSQL **materialized views** (`REFRESH … CONCURRENTLY` + `pg_cron`) or trigger-maintained summary tables; materialized views lose automatic refresh and DML support.
- **Partitioning** is broadly supported via declarative partitioning; PostgreSQL has no `RANGE LEFT` (rewrite boundaries), no `SPLIT`/`MERGE` (still absent in PG 18), `SWITCH` → `DETACH`/`ATTACH`. Foreign keys referencing partitioned tables **are** supported (PG 12+). Always add a `DEFAULT` partition.
