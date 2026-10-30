# Physical Storage — Oracle → Aurora MySQL Reference

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> Section: Physical storage

Reference files distilled from the AWS Oracle to Aurora MySQL Migration Playbook,
physical-storage chapter.

| File | Topic | Conversion category | SCT automation |
|---|---|---|---|
| [table-partitioning.md](table-partitioning.md) | Oracle and MySQL table partitioning | Assisted (★★★) | Partitioning action code; no support for interval/advisor/preference/virtual-column/automatic-list |
| [sharding.md](sharding.md) | Oracle sharding | Blocked (no compatibility) | N/A |

## Quick guidance

- **Partitioning** converts with assistance: hash, list, range, composite/subpartitioning, split, and exchange all have MySQL equivalents. Adjust datatypes, drop tablespace clauses, and use `KEY`/`LIST COLUMNS`/`RANGE COLUMNS` for non-integer keys. Interval, partition advisor, preference, virtual-column, and automatic list partitioning are unsupported in Aurora MySQL.
- **Sharding** has no MySQL equivalent — re-architect at the application tier or adopt a purpose-built store (Amazon Redshift, EMR, or DynamoDB).

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): partitioned tables cannot have FKs (1506) and every unique key must include the partition columns (1503); `REORGANIZE PARTITION` splits any partition; no built-in sharding (Limitless is PostgreSQL-only).
