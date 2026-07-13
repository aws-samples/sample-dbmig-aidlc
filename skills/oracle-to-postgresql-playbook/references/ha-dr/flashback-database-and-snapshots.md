# Oracle Flashback Database and PostgreSQL Amazon Aurora Snapshots

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.hadr.flashback.html

**Conversion category:** Manual (Five-star feature compatibility — storage-level backup managed by Amazon RDS)
**SCT automation:** N/A

## Oracle

Oracle Flashback Database protects against human errors by reverting the entire database to a previous point in time using SQL commands. It uses a self-logging mechanism that captures all changes and stores previous versions of modifications in the configured **Fast Recovery Area**.

You can restore an entire database to a user-created restore point, a timestamp, or a specific System Change Number (SCN).

Examples:

```sql
-- Create a guaranteed restore point
CREATE RESTORE POINT before_update GUARANTEE FLASHBACK DATABASE;

-- Flashback to a restore point
shutdown immediate;
startup mount;
flashback database to restore point before_update;

-- Flashback to a specific time
shutdown immediate;
startup mount;
FLASHBACK DATABASE TO TIME "TO_DATE('01/01/2017','MM/DD/YY')";

-- Configure flashback retention period (minutes)
ALTER SYSTEM SET db_flashback_retention_target=2880;
```

See: [FLASHBACK DATABASE](https://docs.oracle.com/en/database/oracle/oracle-database/19/rcmrf/FLASHBACK-DATABASE.html).

## PostgreSQL

Snapshots are the primary backup mechanism for Amazon Aurora databases — fast and nonintrusive. Take them via the Amazon RDS Management Console or the AWS CLI. Unlike RMAN, there is no need for incremental backups. You can restore to the exact time a snapshot was taken or to any other point in time.

Backup types:
- **Automated Backups** — always enabled on Aurora; no performance impact.
- **Manual Backups** — create a snapshot any time; no performance impact. Restoring requires creating a **new instance**. Up to **100 manual snapshots** per database.

Console operations:
- **Enable automatic backups / set retention** (equivalent to RMAN `configure retention policy to recovery window of X days`): RDS → Databases → choose/create DB → Additional configuration → set **Backup retention period** in days.
- **Manual snapshot** (equivalent to RMAN `BACKUP DATABASE PLUS ARCHIVELOG`): RDS → Databases → choose DB → Actions → **Take snapshot**.
- **Restore from snapshot** (similar to RMAN `RESTORE DATABASE` + `RECOVER DATABASE`, but creates a new cluster, not in place): RDS → Snapshots → choose snapshot → Actions → **Restore snapshot** → enter DB instance identifier → **Restore DB instance**.
- **Point-in-time restore** (similar to RMAN `SET UNTIL TIME ...` before `RESTORE`/`RECOVER`): RDS → Databases → choose DB → Actions → **Restore to point in time** → select date/time within the backup retention window (launches a new instance).

Default automatic backup windows by region (selected): US East (N. Virginia/Ohio) 03:00–11:00 UTC; US West (Oregon/N. California) 06:00–14:00 UTC; EU (Frankfurt) 20:00–04:00 UTC; EU (Ireland) 22:00–06:00 UTC; EU (London) 06:00–14:00 UTC; AP (Mumbai) 16:30–00:30 UTC; AP (Seoul) 13:00–21:00 UTC; AP (Singapore) 14:00–22:00 UTC; AP (Sydney) 12:00–20:00 UTC; AP (Tokyo) 13:00–21:00 UTC; Canada (Central) 06:29–14:29 UTC; South America (São Paulo) 23:00–07:00 UTC; AWS GovCloud (US) 03:00–11:00 UTC.

### AWS CLI backup and restore operations
Useful for migrating existing automated Oracle RMAN scripts:
- `describe-db-cluster-snapshots` — view all current snapshots.
- `create-db-cluster-snapshot` — create a snapshot ("Restore Point").
- `restore-db-cluster-from-snapshot` — restore a new cluster from a snapshot.
- `create-db-instance` — add instances to the restored cluster.
- `restore-db-cluster-to-point-in-time` — point-in-time recovery.

```bash
# View snapshots
aws rds describe-db-cluster-snapshots

# Create a snapshot (restore point)
aws rds create-db-cluster-snapshot \
  --db-cluster-snapshot-identifier Snapshot_name \
  --db-cluster-identifier Cluster_Name

# Restore a new cluster from a snapshot
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier NewCluster \
  --snapshot-identifier SnapshotToRestore \
  --engine aurora-postgresql

# Add an instance to the restored cluster
aws rds create-db-instance \
  --region us-east-1 \
  --db-subnet-group default \
  --engine aurora-postgresql \
  --db-cluster-identifier NewCluster \
  --db-instance-identifier newinstance-nodeA \
  --db-instance-class db.r4.large

# Point-in-time restore
aws rds restore-db-cluster-to-point-in-time \
  --db-cluster-identifier clusternamerestore \
  --source-db-cluster-identifier clustername \
  --restore-to-time 2017-09-19T23:45:00.000Z

aws rds create-db-instance \
  --region us-east-1 \
  --db-subnet-group default \
  --engine aurora-postgresql \
  --db-cluster-identifier clustername-restore \
  --db-instance-identifier newinstance-nodeA \
  --db-instance-class db.r4.large
```

## Conversion notes

| Task | Oracle | Amazon Aurora |
|---|---|---|
| Create a restore point | `CREATE RESTORE POINT before_update GUARANTEE FLASHBACK DATABASE;` | `aws rds create-db-cluster-snapshot --db-cluster-snapshot-identifier Snapshot_name --db-cluster-identifier Cluster_Name` |
| Configure retention period | `ALTER SYSTEM SET db_flashback_retention_target=2880;` | Configure **Backup retention window** via console or CLI. |
| Flashback to a previous restore point | `shutdown immediate; startup mount; flashback database to restore point before_update;` | Create new cluster from a snapshot (`restore-db-cluster-from-snapshot`) + add instance (`create-db-instance`). |
| Flashback to a point in time | `shutdown immediate; startup mount; FLASHBACK DATABASE TO TIME "TO_DATE('01/01/2017','MM/DD/YY')";` | `restore-db-cluster-to-point-in-time --restore-to-time ...` + add instance. |

- Major gotcha: Oracle Flashback Database reverts **in place**; Aurora restore always creates a **new cluster/instance** — plan for endpoint cutover after restore.
- Aurora has no concept of incremental backups; snapshots + continuous PITR cover the same need.
- Up to 100 manual snapshots per database; automated backups are always on with a configurable retention window.
