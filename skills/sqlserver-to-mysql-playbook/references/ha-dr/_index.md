# High availability and disaster recovery — reference index

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.hadr.html

Reference files distilled from the HA/DR chapter of the AWS SQL Server 2019 → Amazon Aurora
MySQL Migration Playbook.

| File | Topic | Conversion category | SCT automation |
|---|---|---|---|
| `hadr.md` | High availability and disaster recovery (chapter overview) | N/A (infra) | N/A |
| `backup-restore.md` | Backup and restore design | N/A (infra) | No automation (action code: Backup) |
| `essentials.md` | High availability essentials | N/A (infra) | N/A |

## Summary
- **Backup and restore design** — SQL Server recovery models and full/differential/log
  backups vs. Aurora MySQL continuous storage-level backups, point-in-time restore (1–35 days),
  manual snapshots, backtracking, cloning, and S3 import/export (`SELECT … INTO OUTFILE S3` /
  `LOAD DATA FROM S3`).
- **High availability essentials** — SQL Server FCI, Always On Availability Groups, Database
  Mirroring, and Log Shipping vs. Aurora MySQL managed multi-AZ clusters, Aurora replicas
  (up to 15), cluster/reader/instance endpoints, storage auto-repair, survivable cache
  warming, crash recovery, and delayed replication.
