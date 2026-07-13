# Oracle Active Data Guard and PostgreSQL Replicas

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.hadr.replicates.html

**Conversion category:** Manual (Three-star feature compatibility — distribute load/applications/users across multiple instances)
**SCT automation:** N/A

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
- **Multi-AZ (Availability Zone)** — replicating instance in a different region.
- **Instance Read Replicas** — replicating instance in the same region.

Instance options:
- **Create Aurora Replica** — same region.
- **Create Cross Region Read Replica** — new reader cluster in a different region.

Differences between the two:
- Cross Region creates a new reader cluster in a different region — higher level of HA and keeps data closer to end users.
- Cross Region has more lag between instances.
- Additional charges apply for cross-region data transfer.

Behavioral notes:
- DDL statements on the primary may interrupt connections on associated Aurora Replicas (if a replica connection is actively using an object modified by DDL on the primary).
- Rebooting the primary instance automatically reboots the Aurora Replicas in that cluster.
- Before creating a cross-region replica, turn on the `binlog_format` parameter.

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
| Switch over | `ALTER DATABASE SWITCHOVER TO DBREP VERIFY;` | Can't choose which instance to fail over to; the instance with higher priority becomes the writer (primary). |
| Automatic failover | `EDIT DATABASE ... SET PROPERTY FASTSTARTFAILOVERTARGET=...; ENABLE FAST_START FAILOVER;` | Use Multi-AZ on instance creation or by modifying an existing instance. |
| Sync vs async | Configurable (MAXIMIZE AVAILABILITY / MAXIMIZE PERFORMANCE) | **Not supported** — only asynchronous replication. |
| Open standby to R/W and continue syncing | `CONVERT DATABASE ... TO SNAPSHOT STANDBY;` then `TO PHYSICAL STANDBY;` | **Not supported** — instead restore from snapshot, run QA/testing on the restored instance, then drop it. |
| Gapped (delayed) replication | `ALTER DATABASE RECOVER MANAGED STANDBY DATABASE DELAY 5 ...` | **Not supported.** |

- Aurora replication latency is in milliseconds; promotion of a replica to primary is typically under 30 seconds with no data loss.
- Key tradeoff: Aurora simplifies HA/DR management at the cost of Oracle ADG flexibility (no sync mode, no delayed standby, no manual failover target selection).
