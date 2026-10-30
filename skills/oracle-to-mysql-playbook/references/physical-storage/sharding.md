# Oracle Sharding

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.storage.sharding.html

**Conversion category:** Blocked (no feature compatibility; no automation)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): No built-in sharding on 3 / 8.4 (Limitless is PostgreSQL-only); scale-up/read-out check first; Vitess/ProxySQL/per-tenant clusters; cross-shard limits.

MySQL does not support sharding. There is no direct equivalent for Oracle's sharded database architecture.

## Oracle

Sharding is a data architecture where table data is horizontally partitioned across independent databases called *shards*. All shards together form a single logical database, the *sharded database (SDB)*. Sharding a table splits it across shards, where each shard holds a sharded table with the same structure but a different subset of rows.

Oracle 18c sharding enhancements:
- **User-defined sharding** — before 18c data was distributed across shards by the system; user-defined sharding lets users explicitly redirect sharded table data to specific individual shards.
- **JSON, BLOB, CLOB, and spatial objects** can now be used in sharded tables.

(See "Overview of Oracle Sharding" in the Oracle documentation.)

## MySQL

There is no equivalent option in MySQL. Options:

- **Application-level sharding** — build sharding management in the application that interacts with data spread across multiple instances.
- **Use a different data store** — assess requirements and consider Amazon Redshift, Amazon EMR, or Amazon DynamoDB.

## Conversion notes

- No automated conversion path; this is a manual re-architecture effort.
- Aurora MySQL has no native sharding feature equivalent to Oracle SDB.
- Horizontal scale must be handled in the application tier (routing/sharding logic across multiple instances) or by adopting a purpose-built data store (Redshift, EMR, DynamoDB).
- Oracle-specific sharded-table features (user-defined sharding; JSON/BLOB/CLOB/spatial in shards) have no MySQL counterpart.
- Still true for Aurora MySQL 3 and 8.4: there is no built-in sharding. **Aurora Limitless Database** (managed horizontal scaling) is available for Aurora PostgreSQL only.
- Before sharding, check whether one Aurora writer is enough: a single cluster scales up to large instance classes (or 256 ACU Serverless v2 instances), up to 15 readers, and storage up to the Aurora cluster-volume limit.
- Application-level sharding options: a shard map in the application (AWS JDBC wrapper does not route shards), proxies such as Vitess or ProxySQL on EC2/EKS, or one Aurora cluster per tenant/region with a routing table.
- Cross-shard queries and transactions have no in-database support (no XA through Aurora writer failover, no database links); aggregate in the application or in an analytics store (zero-ETL to Redshift).
