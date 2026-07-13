# Oracle Flashback Database and MySQL snapshots

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.hadr.flashback.html

**Conversion category:** Manual (three-star feature compatibility — storage-level backup is managed by Amazon RDS)
**SCT automation:** N/A

## Oracle

Oracle Flashback Database reverts an entire database to a previous point in time using SQL. It self-logs all changes, storing previous versions of modifications in the Fast Recovery Area. You can restore to a user-created restore point, a timestamp, or a System Change Number (SCN).

### Examples

Create a guaranteed restore point:

```
CREATE RESTORE POINT before_update GUARANTEE FLASHBACK DATABASE;
```

Flashback to a restore point:

```
shutdown immediate;
startup mount;
flashback database to restore point before_update;
```

Flashback to a specific time:

```
shutdown immediate;
startup mount;
FLASHBACK DATABASE TO TIME "TO_DATE('01/01/2017','MM/DD/YY')";
```

See [FLASHBACK DATABASE](https://docs.oracle.com/en/database/oracle/oracle-database/19/rcmrf/FLASHBACK-DATABASE.html) in the Oracle documentation.

## MySQL

Snapshots are the primary backup mechanism for Aurora — fast, nonintrusive, no incremental backups needed. Take them via the RDS console or AWS CLI; restore to the snapshot time or to any point in time.

- **Automated backups** — always enabled; no performance impact.
- **Manual backups** — create a snapshot anytime; restore creates a **new instance**; up to 100 manual snapshots per database.

On Aurora MySQL 5.6 compatible, the **Aurora Backtrack** feature is the equivalent of Oracle Flashback Database. It must be opted into at cluster **create or restore** time — it cannot be enabled on a running cluster.

Backtrack one day (86,400 seconds):

```
aws rds modify-db-cluster --db-cluster-identifier sample-cluster --backtrack-window 86400
```

Monitor backtrack:

```
aws rds describe-db-cluster-backtracks --db-cluster-identifier sample-cluster
```

### Backup retention (equivalent to RMAN retention policy)

Console: RDS → **Databases** → select/create database → **Additional configuration** → set **Backup retention period** (days). Default automatic backup windows vary by region (examples): US East (N. Virginia/Ohio) 03:00–11:00 UTC; US West (Oregon/N. California) 06:00–14:00 UTC; EU (Ireland) 22:00–06:00 UTC; EU (Frankfurt) 20:00–04:00 UTC; EU (London) 06:00–14:00 UTC; AP (Tokyo/Seoul) 13:00–21:00 UTC; AP (Singapore) 14:00–22:00 UTC; AP (Sydney) 12:00–20:00 UTC; AP (Mumbai) 16:30–00:30 UTC; Canada (Central) 06:29–14:29 UTC; South America (São Paulo) 23:00–07:00 UTC; AWS GovCloud (US) 03:00–11:00 UTC.

Manual snapshot (≈ `BACKUP DATABASE PLUS ARCHIVELOG`): RDS → **Databases** → select → **Actions** → **Take snapshot**.

Restore from snapshot (≈ RMAN `RESTORE`/`RECOVER`, but creates a **new cluster**): RDS → **Snapshots** → select → **Actions** → **Restore snapshot** → set DB instance identifier → **Restore DB instance**.

Point-in-time restore (≈ RMAN `SET UNTIL TIME` + restore/recover): RDS → **Databases** → select → **Actions** → **Restore to point in time** → choose date/time within the retention window (launches a new instance).

### AWS CLI backup and restore

```
aws rds describe-db-cluster-snapshots

aws rds create-db-cluster-snapshot
    --db-cluster-snapshot-identifier Snapshot_name
    --db-cluster-identifier Cluster_Name

aws rds restore-db-cluster-from-snapshot
    --db-cluster-identifier NewCluster
    --snapshot-identifier SnapshotToRestore
    --engine aurora-mysql

aws rds create-db-instance
    --region us-east-1
    --db-subnet-group default
    --engine aurora-mysql
    --db-cluster-identifier NewCluster
    --db-instance-identifier newinstance-nodeA
    --db-instance-class db.r4.large
```

Point-in-time recovery:

```
aws rds restore-db-cluster-to-point-in-time
    --db-cluster-identifier clusternamerestore
    --source-db-cluster-identifier clustername
    --restore-to-time 2017-09-19T23:45:00.000Z

aws rds create-db-instance
    --region us-east-1
    --db-subnet-group default
    --engine aurora-mysql
    --db-cluster-identifier clustername-restore
    --db-instance-identifier newinstance-nodeA
    --db-instance-class db.r4.large
```

### Summary mapping

| Task | Oracle | Amazon Aurora |
|---|---|---|
| Create a restore point | `CREATE RESTORE POINT before_update GUARANTEE FLASHBACK DATABASE;` | `aws rds create-db-cluster-snapshot --db-cluster-snapshot-identifier Snapshot_name --db-cluster-identifier Cluster_Name` |
| Configure retention | `ALTER SYSTEM SET db_flashback_retention_target=2880;` | Set **Backup retention window** (console or CLI) |
| Flashback to a restore point | `flashback database to restore point before_update;` | Create a new cluster from a snapshot (`restore-db-cluster-from-snapshot` + `create-db-instance`) |
| Flashback to a point in time | `FLASHBACK DATABASE TO TIME "TO_DATE('01/01/2017','MM/DD/YY')";` | `aws rds modify-db-cluster --db-cluster-identifier sample-cluster --backtrack-window 86400` |

## Conversion notes
- No SQL-level equivalent — Oracle's in-place `FLASHBACK DATABASE` is replaced by RDS-managed snapshots, point-in-time restore, and (on Aurora MySQL 5.6) Backtrack.
- Key difference: snapshot/PITR restores create a **new cluster/instance** rather than rewinding in place; Backtrack is the closest in-place rewind but must be enabled at create/restore time and cannot be turned on for a running cluster.
- Oracle retention is set via `db_flashback_retention_target` (minutes) and the Fast Recovery Area; Aurora uses the backup retention window plus the backtrack window.
- No `shutdown immediate; startup mount;` step — Aurora operations are online via console/CLI.
