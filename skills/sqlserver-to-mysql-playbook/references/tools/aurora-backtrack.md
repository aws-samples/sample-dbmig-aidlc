# Amazon Aurora Backtrack Overview

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.aurorabacktrack.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A — Aurora MySQL operational feature.

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
- Available only in certain AWS Regions and specific Aurora MySQL versions.
- Only for clusters **created with Backtrack enabled** (or restored snapshot/clone with it enabled); can't enable on clusters created with it turned off.
- Backtrack window limit: **72 hours**.
- Affects the **entire** DB cluster — can't backtrack a single table or single update.
- Not supported with binlog replication; cross-Region replication must be turned off first.
- Can't backtrack a database clone to before the clone was created (but the original DB can backtrack to before the clone).
- Causes brief DB instance disruption — stop/pause applications first; Aurora pauses the DB, closes connections, drops uncommitted reads/writes during the operation.
- **Not supported in regions:** Africa (Cape Town), China (Ningxia), Asia Pacific (Hong Kong), Europe (Milan), Europe (Stockholm), Middle East (Bahrain), South America (São Paulo).
- Can't restore a cross-region snapshot of a backtrack-enabled cluster in a Region that doesn't support backtracking.
- Can't use backtrack with Aurora multi-master clusters.
- After an in-place upgrade from Aurora MySQL v1 to v2, can't backtrack to before the upgrade.
