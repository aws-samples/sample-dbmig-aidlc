# Oracle Recovery Manager and Amazon RDS snapshots

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.hadr.rman.html

**Conversion category:** Manual (three-star feature compatibility — storage-level backup managed by Amazon RDS)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): ALTER INSTANCE DISABLE INNODB REDO_LOG not available on Aurora (verified error 1227 on both); AWS Backup, snapshot export, fast clone for VALIDATE/DUPLICATE, current instance class.

## Oracle

Oracle Recovery Manager (RMAN) is the primary backup and recovery tool, with its own scripting syntax for full or incremental backups. It supports online backups when the database runs in Archived Log Mode.

Backup types:
- **Full** — full backup of the whole database or individual data files (e.g., level 0).
- **Differential incremental** — blocks changed since the previous level 0 or 1 backup.
- **Cumulative incremental** — blocks changed since the previous level 0 backup.

RMAN backs up data files, the control file, the parameter file, and archived redo logs.

### Examples

Connect:

```
export ORACLE_SID=ORCL
rman target=/
```

Full backup with archived redo logs:

```
BACKUP DATABASE PLUS ARCHIVELOG;
```

Incremental backups:

```
BACKUP INCREMENTAL LEVEL 0 DATABASE;
BACKUP INCREMENTAL LEVEL 1 DATABASE;
```

Restore a database:

```
RUN {
SHUTDOWN IMMEDIATE;
STARTUP MOUNT;
RESTORE DATABASE;
RECOVER DATABASE;
ALTER DATABASE OPEN;
}
```

Restore specific pluggable databases (12c):

```
RUN {
ALTER PLUGGABLE DATABASE pdbA, pdbB CLOSE;
RESTORE PLUGGABLE DATABASE pdbA, pdbB;
RECOVER PLUGGABLE DATABASE pdbA, pdbB;
ALTER PLUGGABLE DATABASE pdbA, pdbB OPEN;
}
```

Restore to a point in time:

```
RUN {
SHUTDOWN IMMEDIATE;
STARTUP MOUNT;
SET UNTIL TIME "TO_DATE('20-SEP-2017 21:30:00','DD-MON-YYYY HH24:MI:SS')";
RESTORE DATABASE;
RECOVER DATABASE;
ALTER DATABASE OPEN RESETLOGS;
}
```

List backups:

```
LIST BACKUP OF DATABASE;
```

See [Backup and Recovery User Guide](https://docs.oracle.com/en/database/oracle/oracle-database/19/bradv/index.html) in the Oracle documentation.

## MySQL

Snapshots are the primary backup mechanism for Aurora — fast, nonintrusive, no incremental backups needed. Take them via the RDS console or AWS CLI; restore to the snapshot time or any point in time.

- **Automated backups** — always enabled; no performance impact.
- **Manual backups** — create anytime; restore creates a **new instance**; up to 100 manual snapshots per database.

Note: `ALTER INSTANCE DISABLE INNODB REDO_LOG` (an RDS for MySQL 8.0.21+ bulk-load option) is **not available on Aurora**: the master user lacks `INNODB_REDO_LOG_ENABLE` (error 1227, verified on 3.13 and 8.4.8), and Aurora's storage layer depends on the redo stream.

### Summary mapping

| Task | Oracle RMAN | Amazon Aurora |
|---|---|---|
| Scheduled backups | `DBMS_SCHEDULER` job running an RMAN script | Automatic |
| Manual full backup | `BACKUP DATABASE PLUS ARCHIVELOG;` | `aws rds create-db-cluster-snapshot --db-cluster-snapshot-identifier Snapshot_name --db-cluster-identifier Cluster_Name` |
| Restore database | `RUN { SHUTDOWN IMMEDIATE; STARTUP MOUNT; RESTORE DATABASE; RECOVER DATABASE; ALTER DATABASE OPEN; }` | `restore-db-cluster-from-snapshot` then `create-db-instance` (creates a new cluster) |
| Incremental differential | `BACKUP INCREMENTAL LEVEL 0/1 DATABASE;` | N/A |
| Incremental cumulative | `BACKUP INCREMENTAL LEVEL 0/1 CUMULATIVE DATABASE;` | N/A |
| Restore to a point in time | `RUN { ... SET UNTIL TIME "..."; RESTORE DATABASE; RECOVER DATABASE; ALTER DATABASE OPEN RESETLOGS; }` | `restore-db-cluster-to-point-in-time --restore-to-time ...` then `create-db-instance` |
| Backup archive logs | `BACKUP ARCHIVELOG ALL;` | N/A |
| Delete old archive logs | `CROSSCHECK BACKUP; DELETE EXPIRED BACKUP;` | N/A |
| Restore single PDB (12c) | `RUN { ALTER PLUGGABLE DATABASE ... CLOSE; RESTORE/RECOVER PLUGGABLE DATABASE ...; ALTER PLUGGABLE DATABASE ... OPEN; }` | Restore new cluster from snapshot, add instance, then copy the database back with `mysqldump`/`mysql` |

CLI restore example:

```
aws rds restore-db-cluster-from-snapshot
  --db-cluster-identifier NewCluster
  --snapshot-identifier SnapshotToRestore
  --engine aurora-mysql

aws rds create-db-instance
  --region us-east-1
  --db-subnet-group default
  --engine aurora-mysql
  --db-cluster-identifier clustername-restore
  --db-instance-identifier newinstance-nodeA
  --db-instance-class db.r7g.large      # r4 classes are retired
```

Point-in-time restore:

```
aws rds restore-db-cluster-to-point-in-time
  --db-cluster-identifier clustername-restore
  --source-db-cluster-identifier clustername
  --restore-to-time 2017-09-19T23:45:00.000Z
```

Copy a single database back to the original instance:

```
mysqldump --column-statistics=0 DATABASE_TO_RESTORE -h RESTORED_INSTANCE_ENDPOINT -P 3306 -u USER_NAME -p > /local_path/backup-file.sql
mysql DB_NAME -h MYSQL_INSTANCE_ENDPOINT -P 3306 -u USER_NAME -p < /local_path/backup-file.sql
```

(`--column-statistics=0` is only needed when an 8.x client dumps a 5.7 server; MySQL Shell `util.dumpSchemas()`/`util.loadDump()` is faster for large databases.)

## Conversion notes
- No automated conversion — RMAN scripts are replaced by RDS-managed snapshots, automated backups, and point-in-time restore.
- Incremental backups (differential/cumulative), explicit archive-log backup/cleanup, and `CROSSCHECK`/`DELETE EXPIRED` have **no Aurora equivalent** — Aurora's continuous backup to the storage layer makes them unnecessary.
- Restores always produce a **new cluster/instance**; there is no in-place `RESTORE`/`RECOVER`. Object-level (single PDB/database) recovery requires restoring a new cluster and copying the data back via mysqldump/mysql.
- Existing automated RMAN shell scripts map most naturally to AWS CLI `rds` commands for migration.
- Retention is 1–35 days for automated backups; use **AWS Backup** plans for longer retention, cross-Region and cross-account copies (≈ RMAN backup to tape/secondary site).
- **Snapshot export to S3** (Parquet) gives a portable copy for analytics or long-term archive.
- RMAN `VALIDATE`/`DUPLICATE` → restore or **fast-clone** the cluster and run checks there; clones are copy-on-write and take minutes.
- Test restores regularly: restore time grows with database size, unlike Backtrack.
