# Amazon Aurora Backtrack

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tools.aurorabacktrack.html

**Conversion category:** N/A (Aurora MySQL operational feature)
**SCT automation:** N/A

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

- Available only in certain AWS Regions and specific Aurora MySQL versions.
- Only available for clusters **created with the Backtrack feature enabled** (at creation or when restoring a snapshot). You can create a clone with backtrack enabled. You **cannot** enable backtracking on a cluster created with it turned off.
- Maximum backtrack window: **72 hours**.
- Affects the **entire DB cluster** — you can't selectively backtrack a single table or data update.
- Not supported with binary log (binlog) replication. Cross-Region replication must be turned off before configuring/using backtracking.
- You can't backtrack a database clone to a time before the clone was created (but the original database can backtrack to before the clone was created).
- Causes a brief DB instance disruption — stop/pause applications first. During the operation Aurora pauses the database, closes open connections, and drops uncommitted reads/writes.
- Not supported in these Regions: Africa (Cape Town), China (Ningxia), Asia Pacific (Hong Kong), Europe (Milan), Europe (Stockholm), Middle East (Bahrain), South America (São Paulo).
- You can't restore a cross-Region snapshot of a backtrack-enabled cluster in a Region that doesn't support backtracking.
- Can't use backtrack with Aurora multi-master clusters.
- After an in-place upgrade from Aurora MySQL version 1 to version 2, you can't backtrack to a point in time before the upgrade.

See: "Amazon Aurora Backtrack — Turn Back Time".

## Conversion notes

- An operational safety-net for the Aurora MySQL target; not part of schema conversion.
- Useful during migration cutover and post-migration validation — quickly undo a bad data load or destructive statement without a hours-long PITR.
- Must be **enabled at cluster creation** (or snapshot restore/clone) — plan for it before cutover; it can't be turned on later.
- Incompatible with binlog replication / cross-Region replication and multi-master — incompatible with some HA/replication cutover designs.
- Whole-cluster only and capped at 72 hours; keep regular backups for longer-horizon or granular recovery.
