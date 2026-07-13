# High Availability & Disaster Recovery — Reference Index

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> Section: High availability and disaster recovery

Distilled reference material on backup/restore and HA/DR mapping between
Microsoft SQL Server and Amazon Aurora PostgreSQL.

| File | Topic | Conversion category | SCT automation |
|---|---|---|---|
| [backup-and-restore.md](backup-and-restore.md) | Backup and restore design — recovery models, backup types, restore sequences vs. Aurora continuous backup, PITR, snapshots, cloning | N/A (infra) | N/A — storage-level backup managed by RDS |
| [high-availability-essentials.md](high-availability-essentials.md) | HA/DR solutions — FCI, Always On AGs, Mirroring, Log Shipping vs. Aurora clusters, replicas, endpoints, storage auto-repair | N/A (infra) | N/A |

## Key takeaways

- Aurora PostgreSQL delivers HA and backup as a **managed service**, not via DDL/scripts. There is no datatype/feature rule conversion here — these are infrastructure topics.
- **Backup:** Aurora ≈ SQL Server `FULL` recovery model; continuous incremental backups, 1–35 day point-in-time restore, manual snapshots, copy-on-write cloning. No log/differential/partial backups; automated backups cannot be disabled.
- **HA:** clustering and storage replication are automatic across **three Availability Zones**. FCI/Log Shipping have no equivalent; Always On Availability Groups map to **Aurora Replicas** (up to 15 + primary). Failover is via the **cluster endpoint**; read scale-out via the **reader endpoint**.
