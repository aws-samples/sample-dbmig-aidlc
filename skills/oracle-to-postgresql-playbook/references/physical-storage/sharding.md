# Oracle Sharding

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.storage.sharding.html

**Conversion category:** Blocked (No feature compatibility, no automation). PostgreSQL does not support sharding as a built-in feature.
**SCT automation:** No automation. AWS SCT action code index: N/A. Key difference: PostgreSQL doesn't support sharding.

## Oracle

Sharding is a data architecture where table data is horizontally partitioned across independent databases called shards. All shards together form a single logical database called a sharded database (SDB). Sharding a table splits it across shards, where each shard holds a sharded table with the same structure but a different subset of rows. This improves performance and availability.

Oracle 18c sharding enhancements:
- **User-defined sharding** — Before 18c, the system redirected data across shards. With user-defined sharding, users can explicitly direct sharded table data to specific individual shards.
- **`JSON`, `BLOB`, `CLOB`, and spatial objects** can now be used in sharded tables.

For more information, see [Oracle Sharding Overview](https://docs.oracle.com/en/database/oracle/oracle-database/19/shard/sharding-overview.html) in the Oracle documentation.

## PostgreSQL

PostgreSQL does not support sharding as a native/built-in feature, so there is no direct equivalent. With AWS DMS you can migrate data from a sharded Oracle database into an Amazon Aurora cluster. The horizontal-partitioning behavior must be re-architected rather than translated 1:1.

## Conversion notes

- This is a blocked feature: there is no built-in PostgreSQL sharding construct and no SCT/DMS automation for it.
- Migrating off Oracle sharding requires re-architecting the data distribution strategy. Options to consider on Aurora PostgreSQL:
  - Consolidate shard data into a single Aurora PostgreSQL database/cluster (often viable since Aurora scales storage and read replicas independently), using native table partitioning (range/list/hash) for manageability within one database.
  - Implement application-level sharding/routing across multiple Aurora instances if horizontal scale-out across independent databases is still required.
  - Use extensions/external tooling (e.g., partition-based or distributed-PostgreSQL approaches) outside the scope of native PostgreSQL if true distributed sharding is mandatory.
- AWS DMS handles the data movement from each Oracle shard into the chosen Aurora target; the logical re-mapping of shards to the new topology is a manual design decision.
- Validate query patterns, cross-shard joins, and global uniqueness/sequence generation, since these often depend on Oracle sharding semantics that do not carry over.
