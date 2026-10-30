# Amazon Aurora Backtrack Overview

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.aurorabacktrack.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A — Aurora MySQL operational feature.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Backtrack on Aurora MySQL 2/3/8.4 (AWS docs); corrected the binlog restriction, removed the stale Region list and multi-master, 3→8.4 upgrade caveat, CLI commands and SQL Server snapshot analogy.

## SQL Server
N/A on the source side. Conceptually analogous to point-in-time recovery, but faster — relevant for operational resilience after migrating off SQL Server.

## MySQL
Aurora Backtrack is an Aurora MySQL feature that rewinds the DB cluster to a specified point in time without restoring from a backup or launching a new cluster. It uses Aurora's distributed, log-structured storage where each change generates a log record identified by a Log Sequence Number (LSN); enabling backtrack provisions a FIFO buffer of LSNs for fast recovery (seconds).

## Conversion notes
- **Purpose:** Quickly undo mistakes (e.g., a `DELETE` without a `WHERE`, dropping the wrong table) with minimal service interruption.
- **Advantages over backup/restore:** Easily undo destructive actions; rewind in minutes (no new cluster needed); explore earlier data changes by backtracking back and forth to find when a change occurred.
- **Enable:** When creating a new Aurora MySQL DB cluster, choose **Enable Backtrack** and set a **Target Backtrack window** greater than zero. (Also available when restoring a snapshot or cloning.)
- **Operation:** Pause the application, open the Aurora Console, select the cluster, choose **Backtrack DB cluster**, pick the point in time, confirm. Aurora pauses the DB, closes open connections, drops uncommitted writes, performs the rewind (instance state = "backtracking"), then resumes.

### Backtrack window
- **Target window:** The amount of time you want to be able to backtrack (e.g., 24h). You pay an hourly rate to store change records for this window.
- **Actual window:** May be smaller than target, based on workload and storage for change records. Heavy workloads generate more change records; under extremely heavy workload the actual window can be smaller than target (you get a notification).
- Deleted tables are kept in backtrack change records (so you can revert) unless there isn't enough space in the window.

### Backtracking limitations
- Supported on Aurora MySQL version 2, version 3 and version 8.4 in most commercial Regions (all versions in us-east-1/2 and us-west-1/2); check the AWS Region table.
- Only for clusters **created with Backtrack enabled** (or restored snapshot/clone with it enabled); can't enable on clusters created with it turned off.
- Backtrack window limit: **72 hours**.
- Affects the **entire** DB cluster — can't backtrack a single table or single update.
- You **can** enable binary logging on a backtrack-enabled cluster, but a backtrack then fails unless forced, and a forced backtrack breaks binlog replicas and blue/green deployments. Cross-Region read replicas can't be created from a backtrack-enabled cluster (use Global Database for DR).
- Can't backtrack a database clone to before the clone was created (but the original DB can backtrack to before the clone).
- Causes brief DB instance disruption — stop/pause applications first; Aurora pauses the DB, closes connections, drops uncommitted reads/writes during the operation.
- Can't restore a cross-region snapshot of a backtrack-enabled cluster in a Region that doesn't support backtracking.
- After an in-place upgrade (2 → 3, or 3 → 8.4) you can't backtrack to before the upgrade.
- (Aurora multi-master has been retired.)
- Commands: enable with `create-db-cluster … --backtrack-window 86400`; rewind with `aws rds backtrack-db-cluster --backtrack-to <time>`. This is the closest analog to restoring a SQL Server database snapshot (`RESTORE DATABASE … FROM DATABASE_SNAPSHOT`), but for the whole cluster.
