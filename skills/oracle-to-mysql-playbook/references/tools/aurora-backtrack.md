# Amazon Aurora Backtrack

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tools.aurorabacktrack.html

**Conversion category:** N/A (Aurora MySQL operational feature)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Backtrack is supported on Aurora MySQL 2, 3 and 8.4 (AWS docs); corrected the binlog restriction (allowed, but backtrack must then be forced and breaks replicas), removed the stale Region list and multi-master, added the 3→8.4 upgrade caveat.

## Overview

Backtracking rewinds an Aurora MySQL DB cluster to a time you specify — an "undo" for mistakes like a `DELETE` without a `WHERE` clause or dropping the wrong table. It is **not** a replacement for backups / point-in-time restore, but offers these advantages over traditional backup and restore:

- **Easily undo mistakes** — After a destructive action, backtrack to a time before it with minimal interruption of service.
- **Fast** — A point-in-time restore launches a new cluster from backup/snapshot (can take hours). Backtracking doesn't require a new cluster and rewinds in **minutes**.
- **Explore earlier data changes** — Repeatedly backtrack back and forth in time to find when a change occurred (e.g., backtrack 3 hours, then forward 1 hour = 2 hours before original).

Aurora uses a distributed, log-structured storage system; each change generates a log record identified by a **Log Sequence Number (LSN)**. Enabling backtrack provisions a FIFO buffer in the cluster to store LSNs, allowing recovery in seconds.

Enable it when creating a new Aurora MySQL cluster: choose **Enable Backtrack** and set a **Target Backtrack window** greater than zero in the Backtrack section.

To recover after a production error: pause the application → open the Aurora console → select the cluster → **Backtrack DB cluster** → choose the point in time just before the error → **Backtrack DB cluster**. When initiated, Aurora pauses the database, closes open connections, drops uncommitted writes, waits for the backtrack to complete, then resumes. The instance state shows "backtracking" while the rewind is underway.

## Backtrack window

- **Target backtrack window** — The amount of time you want to be able to backtrack (specified when enabling, e.g., 24 hours).
- **Actual backtrack window** — The actual amount you can backtrack, which can be smaller than the target. Based on workload and storage available for **change records**.

As you make updates with backtracking enabled, you generate change records, which Aurora retains for the target window at an hourly storage rate. Heavier workloads store more change records. Usually you can backtrack the full target amount, but under extremely heavy workloads the cluster may not store enough change records and the actual window becomes smaller than the target — Aurora sends a notification when this happens. If you delete a table, Aurora keeps it in backtrack change records so you can revert; if there isn't enough space, the table may eventually be removed from change records.

## Limitations

- Supported on Aurora MySQL version 2, version 3 and version 8.4, in most commercial Regions (all versions in us-east-1, us-east-2, us-west-1, us-west-2); check the Region table in the AWS docs. Not available for Aurora PostgreSQL.
- Only available for clusters **created with the Backtrack feature enabled** (at creation or when restoring a snapshot). You can create a clone with backtrack enabled. You **cannot** enable backtracking on a cluster created with it turned off.
- Maximum backtrack window: **72 hours**.
- Affects the **entire DB cluster** — you can't selectively backtrack a single table or data update.
- You **can** enable binary logging on a backtrack-enabled cluster, but a backtrack then fails unless you force it, and a forced backtrack breaks downstream binlog replicas and blue/green deployments. You can't create cross-Region read replicas from a backtrack-enabled cluster.
- You can't backtrack a database clone to a time before the clone was created (but the original database can backtrack to before the clone was created).
- Causes a brief DB instance disruption — stop/pause applications first. During the operation Aurora pauses the database, closes open connections, and drops uncommitted reads/writes.
- You can't restore a cross-Region snapshot of a backtrack-enabled cluster in a Region that doesn't support backtracking.
- After an in-place upgrade (version 2 → 3, or 3 → 8.4) you can't backtrack to a point in time before the upgrade.
- (Aurora multi-master, mentioned in the original playbook, has been retired.)

See: "Amazon Aurora Backtrack — Turn Back Time".

## Conversion notes

- An operational safety-net for the Aurora MySQL target; not part of schema conversion.
- Useful during migration cutover and post-migration validation — quickly undo a bad data load or destructive statement without a hours-long PITR.
- Must be **enabled at cluster creation** (or snapshot restore/clone) — plan for it before cutover; it can't be turned on later.
- Conflicts with binlog-based designs (a forced backtrack breaks binlog replicas, CDC out of Aurora and blue/green deployments) and blocks cross-Region read replicas; use Aurora Global Database for cross-Region DR instead.
- Whole-cluster only and capped at 72 hours; keep regular backups for longer-horizon or granular recovery.
