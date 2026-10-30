# Oracle Active Data Guard and MySQL replicas

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.hadr.replicas.html

**Conversion category:** N/A (infrastructure / HA topic — three-star feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Global Database and write forwarding as Data Guard / DML-redirect equivalents, verified replica-status views on both versions, reader isolation, multi-master retired.

## Oracle

Oracle Active Data Guard (ADG) is a synced database architecture with primary and standby databases. The difference between Data Guard and ADG is that ADG standby databases allow **read access only**.

ADG components:
- **Primary DB** — main database open to read and write.
- **Redo/Archive** — redo files and archives storing redo entries for recovery.
- **Data Broker** — Data Guard broker service responsible for all failover and syncing.
- **Standby DB** — secondary, read-only, stays in recovery mode until shut down or promoted (failover/switchover).
- **Log Apply** — runs all redo log entries from redo/archive files on the standby.

All components use the SQL*NET protocol.

Special features:
- Choose asynchronous (best performance) or synchronous (best data protection).
- Temporarily convert a standby to a snapshot database for read/write (QA, testing, loads), then switch back.
- Configure a sync gap between primary and standby to guard against human error (e.g., a 12-hour lag).

See [Creating a Physical Standby Database](https://docs.oracle.com/en/database/oracle/oracle-database/19/sbydb/creating-oracle-data-guard-physical-standby.html) in the Oracle documentation.

## MySQL

Aurora replicas scale read operations and increase availability — similar to Oracle ADG but with far less configuration and administration. Manage replicas from the Amazon RDS console or via the AWS CLI for automation.

Two replication options when creating Aurora MySQL instances:
- **Multi-AZ (Availability Zone)** — create a replicating instance (for cross-region, a different region).
- **Instance Read Replicas** — create a replicating instance in the same region.

Two instance options:
- **Create Aurora Replica** — same-region reader.
- **Create Cross Region Read Replica** — new reader cluster in a different region.

Key differences between the two:
- Cross Region creates a new reader cluster in a different region — higher HA, keeps data closer to users.
- Cross Region has more lag between instances.
- Cross-region data transfer incurs additional charges.

Monitor replication lag:
- Query `mysql.ro_replica_status` and check `Replica_lag_in_msec`. This value is published to CloudWatch as the **ReplicaLag** metric.
- Values also appear in `INFORMATION_SCHEMA.REPLICA_HOST_STATUS` in the Aurora MySQL DB cluster.

Behavioral notes:
- DDL on the primary may interrupt connections on associated Aurora Replicas if a replica connection is actively using an object being modified.
- Rebooting the primary automatically reboots the cluster's Aurora Replicas.
- Before creating a cross-region replica, turn on the `binlog_format` parameter.

With Multi-AZ, the primary automatically switches over to the standby replica when:
- The primary instance fails.
- An Availability Zone outage occurs.
- The instance server type is changed.
- The OS is undergoing software patching.
- A manual failover is initiated via reboot with failover.

### Example — create a cross-region read replica (console)

1. Sign in to the AWS console and choose **RDS**.
2. Choose **Instance actions** → **Create cross-Region read replica**.
3. Enter required details and choose **Create**.

After creation, run reads/writes on the primary and read-only operations on the replica.

## Conversion notes
- This is an HA/DR architecture mapping, not a schema object conversion — no SCT automation applies.
- Oracle ADG offers a single physical standby with read access; Aurora supports up to 15 read replicas sharing the same distributed storage volume, with automatic promotion (typically under 30 seconds).
- Aurora replication latency is in milliseconds because replicas read from the shared Aurora storage volume rather than replaying a full redo apply chain like a standalone standby.
- Cross-region read replicas require `binlog_format` to be enabled and incur cross-region data transfer charges.
- **Prefer Aurora Global Database** over binlog cross-Region replicas for DR (supported on Aurora MySQL 3 and 8.4, verified with `describe-db-engine-versions`): storage-level replication with typically sub-second lag, managed switchover/failover, and up to 5 secondary Regions. It is the closest match to Data Guard with Fast-Start Failover.
- **Write forwarding** (local and global; supported on both versions) lets reader instances accept writes and forward them to the writer — the analog of ADG DML redirection. Choose the read-consistency level with `aurora_replica_read_consistency` (`EVENTUAL`, `SESSION`, `GLOBAL`; empty = not enabled, verified).
- Replica lag: `information_schema.replica_host_status` (column `replica_lag_in_milliseconds`) and `mysql.ro_replica_status` exist on both 3.13 and 8.4 (verified); CloudWatch metric `AuroraReplicaLag`.
- On readers the isolation level is `REPEATABLE READ`; `aurora_read_replica_read_committed` = ON gives `READ COMMITTED` there (see `../sql-plsql/transaction-model.md`).
- Aurora multi-master (mentioned in older material) has been retired; there is one writer per cluster.
- Management is console/CLI-driven on Aurora versus broker/SQL*NET configuration in Oracle.
