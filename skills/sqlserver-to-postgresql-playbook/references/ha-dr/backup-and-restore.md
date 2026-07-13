# Backup and Restore Design

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.hadr.backup.html

**Conversion category:** N/A (infrastructure / managed-service topic)
**SCT automation:** N/A — storage-level backup is managed by Amazon RDS

## SQL Server

A *backup* is both the process of copying data and the resulting data set used for safekeeping and disaster recovery. SQL Server copies data and transaction logs to media (tapes, network shares, cloud storage, local files). Backups operate at the database or filegroup level — **table backups are not supported**.

**Recovery model** is a database-level setting controlling transaction log management. Three models exist:
- `SIMPLE` — restore only from full or differential backups (no log backups).
- `FULL` — transaction logs must be backed up; enables point-in-time restore.
- `BULK LOGGED` — like FULL with minimal logging for bulk operations; supports log restore.

`RESTORE` copies data and log pages from a backup, then runs recovery: rolls forward committed transactions not yet flushed and rolls back uncommitted transactions.

Backup types supported:
- **Copy-only** — independent of the standard backup chain; one-off backups that don't interrupt normal operations.
- **Data backups** — copy data files plus the transaction-log activity during the backup (whole DB or part).
- **Database backup** — entire database at the point the backup finished.
- **Differential backup** — only extents modified since the last full backup; depends on that full backup, can't be used alone.
- **Full backup** — a database backup plus the transaction-log records of activity during the backup.
- **Transaction log backups** — log pages only (no data pages), for all activity since the last full or log backup.
- **File backups** — one or more files or filegroups.

SQL Server also supports media families/sets (mirror and stripe backup devices) and, in Enterprise 2008+, backup compression (smaller files, less I/O/network, more CPU).

A typical restore sequence:
1. Restore the most recent full backup.
2. Restore the most recent differential backup.
3. Restore an uninterrupted set of transaction log backups, in order.
4. Recover the database.

For large databases, SQL Server supports data file restore and single Data Page Restore (except for `SIMPLE` recovery model).

### Syntax

```sql
-- Backing up a whole database
BACKUP DATABASE <Database Name> [ <Files / Filegroups> ] [ READ_WRITE_FILEGROUPS ]
  TO <Backup Devices>
  [ <MIRROR TO Clause> ]
  [ WITH [DIFFERENTIAL ]
  [ <Option List> ][;]

BACKUP LOG <Database Name>
  TO <Backup Devices>
  [ <MIRROR TO clause> ]
  [ WITH <Option List> ][;]

-- Restore
RESTORE DATABASE <Database Name> [ <Files / Filegroups> ] | PAGE = <Page ID>
FROM <Backup Devices>
[ WITH [ RECOVERY | NORECOVERY | STANDBY = <Undo File for Log Shipping> } ]
[, <Option List>]
[;]

RESTORE LOG <Database Name> [ <Files / Filegroups> ] | PAGE = <Page ID>
[ FROM <Backup Devices>
[ WITH [ RECOVERY | NORECOVERY | STANDBY = <Undo File for Log Shipping> } ]
[, <Option List>]
[;]
```

### Examples

```sql
-- Full compressed database backup
BACKUP DATABASE MyDatabase TO DISK='C:\Backups\MyDatabase\FullBackup.bak'
WITH COMPRESSION;

-- Log backup
BACKUP DATABASE MyDatabase TO DISK='C:\Backups\MyDatabase\LogBackup.bak'
WITH COMPRESSION;

-- Partial differential backup
BACKUP DATABASE MyDatabase
  FILEGROUP = 'FileGroup1',
  FILEGROUP = 'FileGroup2'
  TO DISK='C:\Backups\MyDatabase\DB1.bak'
  WITH DIFFERENTIAL;

-- Point-in-time restore
RESTORE DATABASE MyDatabase
  FROM DISK='C:\Backups\MyDatabase\FullBackup.bak'
  WITH NORECOVERY;

RESTORE LOG AdventureWorks2012
  FROM DISK='C:\Backups\MyDatabase\LogBackup.bak'
  WITH NORECOVERY, STOPAT = '20180401 10:35:00';

RESTORE DATABASE AdventureWorks2012 WITH RECOVERY;
```

## PostgreSQL

Aurora PostgreSQL **continuously backs up all cluster volumes** and retains restore data for the backup retention period. Backups are incremental and enable point-in-time restore to any point within the retention window. Retention is configurable from **1 to 35 days**. Backups incur no performance impact and cause no service interruption.

You can also manually trigger snapshots of a cluster volume to keep data beyond the retention period and to create new clusters from them. (Manual snapshots incur RDS storage charges.)

**Restoring data** — recover from automatically retained data or from a manual snapshot. The RDS console shows *Latest Restorable Time* (typically within the last ~5 minutes) and *Earliest Restorable Time* (end of the retention period). Both show NULL until a restore completes.

**Database cloning** — fast, cost-effective copies using a copy-on-write protocol; data is copied only when it changes on source or clone. Useful for testing schema/parameter changes, isolating intensive workloads, and dev/test against production copies. Minimal initial storage.

**Copying and sharing snapshots** — within a Region, across Regions, and across accounts. Authorized accounts can restore a shared snapshot without copying first. To copy an automated snapshot to another account: (1) create a manual snapshot from it, (2) copy the manual snapshot to the other account.

**Backup storage** — the sum of all automated and manual snapshots for all instances/clusters per Region. Deleting an instance deletes its automated backups, but you can create a final manual snapshot (manual snapshots are never auto-deleted).

**Retention period** — default is 1 day via RDS API/CLI, 7 days via the Console; modifiable 1–35 days at any time.

**Disabling automated backups** — not possible on Aurora PostgreSQL; backup retention is managed by the cluster.

**Migration considerations** — moving from a self-managed backup policy to a PaaS (Aurora) is a paradigm shift: no transaction logs, filegroups, disk-space, or purge management to worry about. RDS provides continuous backup with point-in-time restore up to 35 days; you mainly set the retention period and take manual snapshots for special cases.

### Example — change retention from 1 to 7 days (RDS Console)

1. RDS Console → **Databases**.
2. Choose the relevant DB identifier.
3. Verify current automatic backup settings.
4. Select the instance with the **writer** role.
5. Choose **Modify** (top right).
6. Set **Backup retention period** to *7 Days*.
7. **Continue** and review the summary.
8. Under **When to apply modifications**, choose *Apply during the next scheduled maintenance window* or *Apply immediately*.
9. Choose **Modify DB instance**.

### Equivalent CLI operations

```bash
# Create a manual cluster snapshot (≈ BACKUP DATABASE)
aws rds create-db-cluster-snapshot \
  --db-cluster-snapshot-identifier Snapshot_name \
  --db-cluster-identifier Cluster_Name

# Restore a new cluster from a snapshot (≈ database clone / restore)
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier NewCluster \
  --snapshot-identifier SnapshotToRestore \
  --engine aurora-postgresql

# Point-in-time restore to a new cluster
aws rds restore-db-cluster-to-point-in-time \
  --db-cluster-identifier clustername-restore \
  --source-db-cluster-identifier clustername \
  --restore-to-time 2017-09-19T23:45:00.000Z

# Add an instance to the new/restored cluster
aws rds create-db-instance --region us-east-1 --db-subnet-group default \
  --engine aurora-postgresql --db-cluster-identifier clustername-restore \
  --db-instance-identifier newinstancenodeA --db-instance-class db.r4.large
```

## Conversion notes

- **No equivalent to recovery models.** Aurora PostgreSQL backup behavior is equivalent to SQL Server's `FULL` recovery model; `SIMPLE`/`BULK LOGGED` have no analog.
- **No explicit log backups.** Backup happens automatically at the storage level — `BACKUP LOG` has no equivalent and is not needed.
- **No differential backups.** Achieve similar outcomes manually with export tools if required.
- **Partial / filegroup backups have no equivalent.** Use export/import utilities (`pg_dump`/`pg_restore`, or SQL Server export with text files) for subset moves.
- **Partial restore** — restore to a new cluster, then copy only the needed data back to the primary.
- **Terminology mismatch:** a SQL Server *database snapshot* ≈ Aurora *database cloning*; an Aurora *database snapshot* ≈ a SQL Server `COPY_ONLY` backup.
- **Point-in-time restore** maps to `restore-db-cluster-to-point-in-time` (always restores to a *new* cluster — you then add an instance), not an in-place `RESTORE … WITH STOPAT`.
- **Aurora HA/backup specifics:** continuous incremental backup with no performance hit, 1–35 day PITR window, cross-Region/cross-account snapshot sharing, and copy-on-write cloning. Automated backups cannot be disabled and are deleted with the instance unless a final manual snapshot is taken.
