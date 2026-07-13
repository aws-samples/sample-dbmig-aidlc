# Oracle Flashback Table and MySQL snapshots

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.hadr.snapshots.html

**Conversion category:** Manual (three-star feature compatibility — storage-level backup managed by Amazon RDS)
**SCT automation:** N/A

## Oracle

Oracle Flashback Table undoes changes to a table and rewinds it to a previous state (not from a backup). While running, the affected tables are locked but the rest of the database stays available.

Requirements/notes:
- If the table structure changed since the restore point, `FLASHBACK` fails.
- Row movement must be turned on.
- The data to restore must still exist in undo (size/retention managed by the DBA).
- You can restore to an SCN, restore point, or timestamp.

### Examples

Flashback by SCN:

```
SELECT CURRENT_SCN FROM V$DATABASE;
FLASHBACK TABLE employees TO SCN 3254648;
```

Flashback by restore point:

```
SELECT NAME, SCN, TIME FROM V$RESTORE_POINT;
FLASHBACK TABLE employees TO RESTORE POINT employees_year_update;
```

Flashback by timestamp:

```
SELECT NAME, VALUE/60 MINUTES_RETAINED
FROM V$PARAMETER
WHERE NAME = 'undo_retention';
FLASHBACK TABLE employees TO
TIMESTAMP TO_TIMESTAMP('2017-09-21 09:30:00', 'YYYY-MM-DD HH:MI:SS');
```

See [Backup and Recovery User Guide](https://docs.oracle.com/en/database/oracle/oracle-database/19/bradv/index.html) in the Oracle documentation.

## MySQL

Snapshots are the primary backup mechanism for Aurora — fast, nonintrusive, no incremental backups needed. Take them via the RDS console or AWS CLI.

- **Automated backups** — always enabled; no performance impact.
- **Manual backups** — create anytime; restore creates a **new instance**; up to 100 manual snapshots per database.

Aurora has no table-level rewind. To recover a single table you restore a snapshot (or PITR) into a **new cluster**, then copy the table back to the original instance with `mysqldbexport`/`mysqldump` and `mysql`.

### Summary mapping

| Task | Oracle | Amazon Aurora |
|---|---|---|
| Create a restore point | `CREATE RESTORE POINT before_update GUARANTEE FLASHBACK DATABASE;` | `aws rds create-db-cluster-snapshot --db-cluster-snapshot-identifier Snapshot_name --db-cluster-identifier Cluster_Name` |
| Configure retention | `ALTER SYSTEM SET db_flashback_retention_target=2880;` | Set **Backup retention window** (console or CLI) |
| Flashback table to a restore point | `flashback database to restore point before_update;` | Restore a new cluster from a snapshot, add an instance, then copy the table back with `mysqldbexport`/`mysql` |
| Flashback table to a point in time | `FLASHBACK DATABASE TO TIME "TO_DATE('01/01/2017','MM/DD/YY')";` | `aws rds restore-db-cluster-to-point-in-time --db-cluster-identifier clustername-restore --source-db-cluster-identifier clustername --restore-to-time 2017-09-19T23:45:00.000Z`, add an instance, then copy the table back |

Restore a new cluster from a snapshot and add an instance:

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
    --db-instance-class db.r4.large
```

## Conversion notes
- No table-level in-place rewind in Aurora — Oracle's `FLASHBACK TABLE` has no direct equivalent.
- Recovery of a single table is a multi-step process: restore snapshot/PITR to a **new** cluster, then selectively export/import the affected table back into the original instance (`mysqldbexport`/`mysqldump` + `mysql`). This is heavier than Oracle's single statement.
- Oracle relies on undo retention + row movement for table flashback; Aurora relies on snapshot/PITR retention windows.
- The summary table on the source page reuses `FLASHBACK DATABASE` syntax for the Oracle column even though the topic is table-level flashback; the actual table-level commands are `FLASHBACK TABLE ... TO SCN | RESTORE POINT | TIMESTAMP` shown in the examples above.
