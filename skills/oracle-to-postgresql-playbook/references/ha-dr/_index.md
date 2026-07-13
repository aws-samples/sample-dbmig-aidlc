# High Availability & Disaster Recovery — Reference Index

Distilled from the AWS *Oracle → Aurora PostgreSQL Migration Playbook* (HA/DR chapter). Reference only — test everything in a non-production environment first.

- [active-data-guard-and-replicas.md](active-data-guard-and-replicas.md) — Oracle Active Data Guard standby databases vs. Aurora read replicas / Multi-AZ (sync, delayed standby, and snapshot-standby gaps noted).
- [rac-and-aurora-architecture.md](rac-and-aurora-architecture.md) — Oracle RAC shared-disk Active-Active clustering vs. Aurora single-primary + read-replica architecture, with full feature comparison.
- [traffic-director-and-rds-proxy.md](traffic-director-and-rds-proxy.md) — Oracle Connection Manager Traffic Director mode vs. Amazon RDS Proxy for connection pooling and HA.
- [data-pump-and-pg-dump-restore.md](data-pump-and-pg-dump-restore.md) — Oracle Data Pump (expdp/impdp) vs. PostgreSQL pg_dump/pg_restore for logical export/import.
- [flashback-database-and-snapshots.md](flashback-database-and-snapshots.md) — Oracle Flashback Database point-in-time revert vs. Aurora snapshots and point-in-time restore (CLI + console).
- [flashback-table-and-snapshots.md](flashback-table-and-snapshots.md) — Oracle Flashback Table single-table rewind vs. Aurora snapshot restore + pg_dump/pg_restore table copy-back.
- [rman-and-rds-snapshots.md](rman-and-rds-snapshots.md) — Oracle RMAN backup/recovery (full, incremental, PITR, PDB) vs. Aurora automated/manual snapshots and PITR.
- [sqlloader-and-pg-dump-restore.md](sqlloader-and-pg-dump-restore.md) — Oracle SQL*Loader flat-file bulk loading vs. PostgreSQL COPY / load-from-S3 / pg_restore.
