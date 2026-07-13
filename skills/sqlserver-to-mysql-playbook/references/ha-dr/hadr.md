# High availability and disaster recovery

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.hadr.html

**Conversion category:** N/A (infrastructure topic)
**SCT automation:** N/A

## SQL Server
This chapter provides reference information for migrating database resiliency features from
Microsoft SQL Server 2019 to Amazon Aurora MySQL. It compares how the two systems handle
backup and recovery, high availability, and disaster recovery.

SQL Server resiliency relies on features such as recovery models, full/differential/log
backups, Always On Failover Cluster Instances, Always On Availability Groups, Database
Mirroring, and Log Shipping.

## MySQL
Aurora MySQL emphasizes cloud-native capabilities like automated continuous storage-level
backups and managed clustering across Availability Zones, removing the need to manage
transaction logs, filegroups, and backup purging manually.

## Conversion notes
- Topics in this chapter:
  - **Backup and restore design** — see `backup-restore.md`
  - **High availability essentials** — see `essentials.md`
- The comparison highlights similarities and differences, emphasizing Aurora MySQL's
  managed, storage-level backup and multi-AZ clustering model.
