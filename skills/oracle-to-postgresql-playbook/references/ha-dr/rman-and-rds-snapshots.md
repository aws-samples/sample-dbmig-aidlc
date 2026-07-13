# Oracle Recovery Manager (RMAN) and Amazon RDS Snapshots

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.hadr.rman.html

**Conversion category:** Manual (Four-star feature compatibility — storage-level backup managed by Amazon RDS)
**SCT automation:** N/A

## Oracle

Oracle Recovery Manager (RMAN) is the primary backup and recovery tool in Oracle, with its own scripting syntax. Backup types:
- **Full RMAN Backup** — full backup of an entire database or individual data files (e.g., level 0).
- **Differential Incremental** — backs up all blocks changed since the previous level 0 or level 1 backup.
- **Cumulative Incremental** — backs up all blocks changed since the previous level 0 backup.

RMAN supports online backups if the database runs in Archived Log Mode. It backs up: database data files, control file, parameter file, and archived redo logs.

Examples:

```bash
# Connect with RMAN CLI
export ORACLE_SID=ORCL
rman target=/
```

```sql
-- Full backup of database + archived redo logs
BACKUP DATABASE PLUS ARCHIVELOG;

-- Incremental level 0 / level 1
BACKUP INCREMENTAL LEVEL 0 DATABASE;
BACKUP INCREMENTAL LEVEL 1 DATABASE;

-- Cumulative incremental
BACKUP INCREMENTAL LEVEL 0 CUMULATIVE DATABASE;
BACKUP INCREMENTAL LEVEL 1 CUMULATIVE DATABASE;

-- Restore a database
RUN {
SHUTDOWN IMMEDIATE;
STARTUP MOUNT;
RESTORE DATABASE;
RECOVER DATABASE;
ALTER DATABASE OPEN;
}

-- Restore a specific pluggable database (12c)
RUN {
ALTER PLUGGABLE DATABASE pdbA, pdbB CLOSE;
RESTORE PLUGGABLE DATABASE pdbA, pdbB;
RECOVER PLUGGABLE DATABASE pdbA, pdbB;
ALTER PLUGGABLE DATABASE pdbA, pdbB OPEN;
}

-- Restore to a specific point in time
RUN {
SHUTDOWN IMMEDIATE;
STARTUP MOUNT;
SET UNTIL TIME "TO_DATE('20-SEP-2017 21:30:00','DD-MON-YYYY HH24:MI:SS')";
RESTORE DATABASE;
RECOVER DATABASE;
ALTER DATABASE OPEN RESETLOGS;
}

-- Backup archive logs
BACKUP ARCHIVELOG ALL;

-- Delete expired backups
CROSSCHECK BACKUP;
DELETE EXPIRED BACKUP;

-- List current backups
LIST BACKUP OF DATABASE;
```

See: [Backup and Recovery User Guide](https://docs.oracle.com/en/database/oracle/oracle-database/19/bradv/index.html).

## PostgreSQL

Snapshots are the primary backup mechanism for Amazon Aurora — fast and nonintrusive, via the RDS console or AWS CLI. Unlike RMAN, no incremental backups are needed; restore to the exact snapshot time or to any point in time.

Backup types:
- **Automated Backups** — always enabled; no performance impact.
- **Manual Backups** — create any time; no performance impact. Restoring requires a **new instance**. Up to **100 manual snapshots** per database.

```bash
# Manual full backup (≈ BACKUP DATABASE PLUS ARCHIVELOG)
aws rds create-db-cluster-snapshot \
  --db-cluster-snapshot-identifier Snapshot_name \
  --db-cluster-identifier Cluster_Name

# Restore a new cluster from a snapshot (≈ RESTORE/RECOVER DATABASE)
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier NewCluster \
  --snapshot-identifier SnapshotToRestore \
  --engine aurora-postgresql

aws rds create-db-instance \
  --region us-east-1 \
  --db-subnet-group default \
  --engine aurora-postgresql \
  --db-cluster-identifier clustername-restore \
  --db-instance-identifier newinstance-nodeA \
  --db-instance-class db.r4.large

# Point-in-time restore (≈ SET UNTIL TIME ... RESTORE/RECOVER)
aws rds restore-db-cluster-to-point-in-time \
  --db-cluster-identifier clustername-restore \
  --source-db-cluster-identifier clustername \
  --restore-to-time 2017-09-19T23:45:00.000Z
```

For a single pluggable database (12c) equivalent, restore a new cluster from a snapshot, add an instance, then copy the database back to the original instance with `pg_dump`/`pg_restore`:

```bash
pg_dump -F c -h hostname.rds.amazonaws.com -U username -d hr -p 5432 > c:\Export\hr.dmp
pg_restore -h restoredhostname.rds.amazonaws.com -U hr -d hr_restore -p 5432 c:\Export\hr.dmp
```

Optionally swap with the old database using `ALTER DATABASE RENAME`.

## Conversion notes

| Task | Oracle RMAN | Amazon Aurora |
|---|---|---|
| Scheduled backups | `DBMS_SCHEDULER` job running an RMAN script | Automatic (always-on automated backups) |
| Manual full backup | `BACKUP DATABASE PLUS ARCHIVELOG;` | RDS dashboard or `aws rds create-db-cluster-snapshot ...` |
| Restore database | `RUN { SHUTDOWN IMMEDIATE; STARTUP MOUNT; RESTORE DATABASE; RECOVER DATABASE; ALTER DATABASE OPEN; }` | `restore-db-cluster-from-snapshot` + `create-db-instance` (creates a new cluster) |
| Incremental differential | `BACKUP INCREMENTAL LEVEL 0/1 DATABASE;` | N/A (no incremental backups) |
| Incremental cumulative | `BACKUP INCREMENTAL LEVEL 0/1 CUMULATIVE DATABASE;` | N/A |
| Restore to point in time | `RUN { ... SET UNTIL TIME "TO_DATE(...)"; RESTORE DATABASE; RECOVER DATABASE; ALTER DATABASE OPEN RESETLOGS; }` | `restore-db-cluster-to-point-in-time --restore-to-time ...` + `create-db-instance` |
| Backup archive logs | `BACKUP ARCHIVELOG ALL;` | N/A |
| Delete old archive logs | `CROSSCHECK BACKUP; DELETE EXPIRED BACKUP;` | N/A |
| Restore a single PDB (12c) | `RUN { ALTER PLUGGABLE DATABASE ... CLOSE; RESTORE/RECOVER PLUGGABLE DATABASE ...; OPEN; }` | Restore new cluster from snapshot + `pg_dump`/`pg_restore` the DB back to the original instance |

- Major gotcha: RMAN restores in place; Aurora restore always creates a **new cluster** — plan endpoint cutover.
- Incremental/cumulative backups and archive-log management have no Aurora equivalent (managed automatically by RDS storage).
- The AWS CLI is especially useful for migrating existing automated RMAN scripts to scheduled AWS automation.
