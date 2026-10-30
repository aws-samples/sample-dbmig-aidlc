# Oracle Active Data Guard and PostgreSQL Replicas

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.hadr.replicates.html

**Conversion category:** Manual (Three-star feature compatibility — distribute load/applications/users across multiple instances)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): fixed the Multi-AZ/cross-Region wording, removed the MySQL-only `binlog_format` step, added targeted failover, Global Database and fast clones.

## Oracle

Oracle Active Data Guard (ADG) is a synced database architecture with primary and standby databases. The difference between Data Guard and ADG is that ADG standby databases allow **read access only**.

ADG architecture components:
- **Primary DB** — main database open to read and write operations.
- **Redo/Archive** — redo files and archives that store the redo entries for recovery.
- **Data Broker** — Data Guard broker service responsible for all failover and syncing operations.
- **Standby DB** — secondary database allowing read operations only; remains in recovery mode until shut down or it becomes primary (failover/switchover).
- **Log Apply** — runs all redo log entries from the redo/archive files on the standby DB.

All components use the SQL*NET protocol.

Special features:
- Choose **asynchronous** (best performance) or **synchronous** (best data protection).
- Temporarily convert a standby to a **snapshot database** for read/write (QA, testing, loads), then switch back to standby.
- Specify a **sync gap** between primary and standby to guard against human error (e.g., a 12-hour delay).

Representative commands:

```sql
-- Switch over
ALTER DATABASE SWITCHOVER TO DBREP VERIFY;

-- Define automatic failover (via Data Guard broker)
EDIT DATABASE db1 SET PROPERTY FASTSTARTFAILOVERTARGET='db1rep';
EDIT DATABASE db1rep SET PROPERTY FASTSTARTFAILOVERTARGET='db1';
ENABLE FAST_START FAILOVER;

-- Change to synchronous
ALTER SYSTEM SET LOG_ARCHIVE_DEST_2='SERVICE=db1rep AFFIRM SYNC VALID_FOR=(ONLINE_LOGFILES,PRIMARY_ROLE) DB_UNIQUE_NAME=db1rep';
ALTER DATABASE SET STANDBY DATABASE TO MAXIMIZE AVAILABILITY;

-- Change to asynchronous
ALTER SYSTEM SET LOG_ARCHIVE_DEST_2='SERVICE=db1rep NOAFFIRM ASYNC VALID_FOR=(ONLINE_LOGFILES,PRIMARY_ROLE) DB_UNIQUE_NAME=db1rep';
ALTER DATABASE SET STANDBY DATABASE TO MAXIMIZE PERFORMANCE;

-- Open standby to read/write then return to standby
CONVERT DATABASE db1rep TO SNAPSHOT STANDBY;
CONVERT DATABASE db1rep TO PHYSICAL STANDBY;

-- Create 5-minute gapped replication
ALTER DATABASE RECOVER MANAGED STANDBY DATABASE CANCEL;
ALTER DATABASE RECOVER MANAGED STANDBY DATABASE DELAY 5 DISCONNECT FROM SESSION;

-- Return to no delay
ALTER DATABASE RECOVER MANAGED STANDBY DATABASE CANCEL;
ALTER DATABASE RECOVER MANAGED STANDBY DATABASE NODELAY DISCONNECT FROM SESSION;
```

## PostgreSQL

Use Aurora replicas to scale read operations and increase availability (analogous to ADG) with far less configuration. Manage replicas from the Amazon RDS console or automate via the AWS CLI.

Two replication options when creating Aurora PostgreSQL instances:
- **Multi-AZ** — Aurora Replicas in other Availability Zones of the same Region. They share the cluster's storage volume and are the failover targets.
- **Cross-Region** — an **Aurora Global Database** secondary cluster in another Region (storage-level replication, typically under 1 second of lag).

Instance options:
- **Add reader** — Aurora Replica in the same Region (up to 15 per cluster).
- **Add AWS Region** — Global Database secondary cluster in a different Region.

Differences between the two:
- A Global Database secondary is a separate reader cluster in a different Region. It gives Region-level DR and keeps data closer to remote users.
- Cross-Region has more lag between instances (typically under 1 second).
- Additional charges apply for cross-region data transfer.

Behavioral notes:
- DDL statements on the primary may interrupt connections on associated Aurora Replicas (if a replica connection is actively using an object modified by DDL on the primary).
- Rebooting the primary instance automatically reboots the Aurora Replicas in that cluster.
- Durability does not depend on replicas. Aurora storage keeps 6 copies across 3 AZs, and a commit is acknowledged only after a 4-of-6 storage quorum, so a committed transaction survives an AZ loss even with zero replicas. Replicas add fast failover and read scaling.

With Multi-AZ, the primary switches over automatically to the standby replica when:
- The primary database instance fails.
- An Availability Zone outage occurs.
- The instance server type is changed.
- The OS is undergoing software patching.
- A manual failover is initiated using reboot with fail-over.

Create a replica/reader (console walkthrough):
1. Sign in to the AWS console and choose **RDS**.
2. Choose **Instance actions** → **Add reader**.
3. Enter required details and choose **Create**.

After creation, run read/write on the primary and read-only on the replica.

## Conversion notes

Comparison of ADG features vs. Aurora PostgreSQL replicas:

| Feature | Oracle Active Data Guard | Aurora PostgreSQL |
|---|---|---|
| Switch over | `ALTER DATABASE SWITCHOVER TO DBREP VERIFY;` | `aws rds failover-db-cluster --db-cluster-identifier c1 --target-db-instance-identifier c1-reader-2` picks the new writer. Automatic failover picks the replica by promotion tier (`--promotion-tier 0–15`). Cross-Region: `aws rds switchover-global-cluster` (planned, no data loss) or `failover-global-cluster` (unplanned). |
| Automatic failover | `EDIT DATABASE ... SET PROPERTY FASTSTARTFAILOVERTARGET=...; ENABLE FAST_START FAILOVER;` | Automatic whenever the cluster has at least one Aurora Replica in another AZ. |
| Sync vs async | Configurable (MAXIMIZE AVAILABILITY / MAXIMIZE PERFORMANCE) | No mode switch. Commits are synchronous to the 6-way storage quorum across 3 AZs (comparable to Maximum Availability inside a Region). Replica caches and Global Database secondaries are asynchronous. Cap cross-Region lag with the `rds.global_db_rpo` cluster parameter (seconds), which delays commits if the RPO would be exceeded. |
| Open standby to R/W and continue syncing | `CONVERT DATABASE ... TO SNAPSHOT STANDBY;` then `TO PHYSICAL STANDBY;` | **Not supported.** Closest equivalent: an **Aurora fast clone** (`aws rds restore-db-cluster-to-point-in-time --restore-type copy-on-write --use-latest-restorable-time`). A clone is a read/write copy ready in minutes that shares unchanged pages. Use it for QA, then delete it. It does not keep syncing. |
| Gapped (delayed) replication | `ALTER DATABASE RECOVER MANAGED STANDBY DATABASE DELAY 5 ...` | **Not supported.** Use point-in-time restore (or a clone at a past time) to recover from human error. |

- Aurora replication latency is in milliseconds; promotion of a replica to primary is typically under 30 seconds with no data loss.
- Key tradeoff: Aurora simplifies HA/DR management at the cost of Oracle ADG flexibility (no delayed standby, no read/write snapshot standby that resyncs).
- Applications should connect through the **cluster (writer) endpoint** and **reader endpoint**, not instance endpoints, so failover needs no reconfiguration. To cut failover time further, use RDS Proxy or the AWS Advanced JDBC/Python/Node.js wrappers, which are topology-aware.
