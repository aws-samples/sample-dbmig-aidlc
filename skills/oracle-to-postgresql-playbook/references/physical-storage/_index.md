# Physical Storage — Reference Index

Distilled references from the AWS Oracle→Aurora PostgreSQL Migration Playbook (physical storage topics).

- [table-partitioning-and-inheritance.md](table-partitioning-and-inheritance.md) — **READ THIS BEFORE CONVERTING ANY PARTITIONED TABLE.** Oracle hash/list/range/composite partitioning vs PostgreSQL declarative partitioning (validated on Aurora PostgreSQL 18), `pg_partman` for interval partitioning, `DETACH`/`ATTACH` for exchange, and the legacy pre-10 inheritance pattern (do not generate); includes full SQL examples and a per-type support matrix. **Runtime-failure risks:** a missing `DEFAULT` partition makes out-of-range **and NULL-key** inserts fail *in production* (`23514`); range partitions need two-sided bounds starting at `MINVALUE`. **Semantic change:** PK/UNIQUE must include the partition key, which weakens uniqueness to per-partition. Partition names are schema-global and collide. (Assisted)
- [sharding.md](sharding.md) — Oracle horizontal sharding across independent shard databases; not supported natively in PostgreSQL, requires re-architecture (Aurora Limitless Database exists only on 16.x), DMS handles data movement. (Blocked)
