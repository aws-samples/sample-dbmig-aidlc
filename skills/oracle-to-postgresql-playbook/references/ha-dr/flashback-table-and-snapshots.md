# Oracle Flashback Table and Amazon Aurora PostgreSQL Snapshots

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.hadr.snapshots.html

**Conversion category:** Manual (Four-star feature compatibility — storage-level backup managed by Amazon RDS)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): fast-clone/PITR + `postgres_fdw` + `MERGE` row copy-back, Flashback Query gap, corrected snapshot quota.

## Oracle

Oracle Flashback Table undoes changes to a table and rewinds it to a previous state (not from backup). While a Flashback Table operation runs, the affected tables are locked, but the rest of the database remains available.

Constraints:
- If the table structure changed since the restore point, the FLASHBACK fails.
- **Row movement must be enabled.**
- The data to restore must still be in the **undo** (the DBA manages undo size and retention).
- A table can be restored to an SCN, a Restore Point, or a Timestamp.

Examples:

```sql
-- Flashback using SCN
SELECT CURRENT_SCN FROM V$DATABASE;
FLASHBACK TABLE employees TO SCN 3254648;

-- Flashback using a Restore Point
SELECT NAME, SCN, TIME FROM V$RESTORE_POINT;
FLASHBACK TABLE employees TO RESTORE POINT employees_year_update;

-- Flashback using a Timestamp (check undo_retention first)
SELECT NAME, VALUE/60 MINUTES_RETAINED
FROM V$PARAMETER
WHERE NAME = 'undo_retention';
FLASHBACK TABLE employees TO
TIMESTAMP TO_TIMESTAMP('2017-09-21 09:30:00', 'YYYY-MM-DD HH:MI:SS');
```

See: [Backup and Recovery User Guide](https://docs.oracle.com/en/database/oracle/oracle-database/19/bradv/index.html).

## PostgreSQL

Aurora has no table-level flashback. Snapshots are the primary backup mechanism — fast and nonintrusive, taken via the RDS console or AWS CLI. Unlike RMAN, no incremental backups are needed; restore to the exact snapshot time or to any point in time.

Backup types:
- **Automated Backups** — always enabled; no performance impact.
- **Manual Backups** — create any time; no performance impact. Restoring requires a **new cluster**. Default quota: 100 manual cluster snapshots per Region (adjustable).

Because Aurora restores create a new cluster/instance, the workflow to recover a single table is: restore a snapshot (or PITR) into a new cluster, then use `pg_dump`/`pg_restore` to copy the recovered table back to the original instance. (See the Flashback Database reference for full snapshot example commands.)

Faster single-table recovery on Aurora PostgreSQL 18:
1. Create a **point-in-time restore** (or a **fast clone**, `--restore-type copy-on-write`) of the cluster at the time before the bad change, and add one instance.
2. Copy only the affected rows back with `postgres_fdw` (available on Aurora 18) instead of a full `pg_dump` of the table:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgres_fdw;
   CREATE SERVER pitr FOREIGN DATA WRAPPER postgres_fdw OPTIONS (host '<pitr-cluster-endpoint>', dbname 'appdb');
   CREATE USER MAPPING FOR CURRENT_USER SERVER pitr OPTIONS (user 'app_restore', password_required 'true');  -- supply the password from Secrets Manager, not a literal
   IMPORT FOREIGN SCHEMA app LIMIT TO (employees) FROM SERVER pitr INTO restore_stage;
   MERGE INTO app.employees t USING restore_stage.employees s ON t.employee_id = s.employee_id
     WHEN MATCHED THEN UPDATE SET salary = s.salary
     WHEN NOT MATCHED THEN INSERT VALUES (s.*);
   ```
3. Delete the restore cluster.

There is no equivalent of Oracle **Flashback Query** (`SELECT … AS OF TIMESTAMP`). If the application relies on it, design history or audit tables (trigger-maintained), or use the PITR/clone approach above for ad-hoc lookups.

## Conversion notes

| Task | Oracle | Amazon Aurora |
|---|---|---|
| Create a restore point | `CREATE RESTORE POINT before_update GUARANTEE FLASHBACK DATABASE;` | `aws rds create-db-cluster-snapshot --db-cluster-snapshot-identifier Snapshot_name --db-cluster-identifier Cluster_Name` |
| Configure retention period | `ALTER SYSTEM SET db_flashback_retention_target=2880;` | Configure **Backup retention window** via console or CLI. |
| Flashback table to a previous restore point | `shutdown immediate; startup mount; flashback database to restore point before_update;` | Create new cluster from snapshot (`restore-db-cluster-from-snapshot`) + add instance, then use `pg_dump`/`pg_restore` to copy the table back to the original instance. |
| Flashback table to a point in time | `shutdown immediate; startup mount; FLASHBACK DATABASE TO TIME "TO_DATE('01/01/2017','MM/DD/YY')";` | `restore-db-cluster-to-point-in-time --restore-to-time ...` + add instance, then `pg_dump`/`pg_restore` the table back to the original instance. |

- Key gotcha: Oracle can rewind a single table in place (fast, surgical); Aurora has no equivalent. Recovering one table means restoring a whole new cluster and copying the table out with `pg_dump`/`pg_restore` — more time/resource intensive.
- Oracle Flashback Table requires row movement enabled and sufficient undo retention; these have no Aurora analog.
- Plan extra storage/time for single-table recovery on Aurora since a full cluster restore is involved. A fast clone is usually the quickest option when the bad change was recent.
