# High availability essentials

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.hadr.essentials.html

**Conversion category:** N/A (infrastructure topic — four-star feature compatibility)
**SCT automation:** N/A

## SQL Server

SQL Server provides several HA/DR solutions: Always On Failover Cluster Instances (FCI),
Always On Availability Groups, Database Mirroring, and Log Shipping. SQL Server 2017 added
read-scale Availability Groups without a cluster, a Minimum Replica Commit setting, and
cross-OS (Windows-Linux) support. SQL Server 2019 added Database Snapshots (read-only,
transactionally consistent static views — useful for reporting and offloading) and
secondary-to-primary connection redirection for Always On Availability Groups.

### Always On Failover Cluster Instances (FCI)
Uses the Windows Server Failover Clustering (WSFC) framework for instance-level redundancy.
An FCI is a SQL Server instance installed across two or more WSFC nodes; it appears as a
single normal instance to clients. On failure of the active node, services move to a standby
node transparently. Benefits:
- Full instance-level protection.
- Automatic failover of resources between nodes.
- Wide range of storage (iSCSI, Fiber Channel, SMB file shares, etc.).
- Multi-subnet support.
- No client reconfiguration after failover.
- Configurable failover policies; automatic health detection and monitoring.

### Always On Availability Groups
The most recent HA/DR solution (introduced in SQL Server 2012), managed at the database
level (more control than FCI), also relying on WSFC. Uses real-time log record delivery to
maintain near real-time readable copies for failover and scale-out reads. Characteristics:
- Up to nine availability replicas: one primary and up to eight secondary readable replicas.
- Asynchronous-commit and synchronous-commit modes.
- Automatic, manual, and forced failover (only forced can cause data loss).
- Secondary replicas allow read-only access and backup offloading.
- Availability Group Listener acts as a virtual server address; routes reads to read-only
  replicas and read-write to primary, enabling fast failover with no client reconfiguration.
- Flexible failover policies; automatic page repair against corruption.
- Encrypted and compressed log transport.
- Rich tooling: T-SQL DDL, SSMS wizards, Always On Dashboard Monitor, PowerShell.

### Database Mirroring
> Note: Deprecated — Microsoft recommends Always On Availability Groups instead.

A legacy near-instantaneous failover solution, similar in concept to Availability Groups but
limited to one database at a time with a single standby replica.

### Log Shipping
One of the oldest, well-tested HA solutions, configured at the database level. Maintains one
or more secondary databases for a single primary via three steps:
1. Back up the transaction log of the primary.
2. Copy the log backup file to a secondary server.
3. Restore the log backup to apply changes to the secondary.

Repeat steps 2–3 per secondary. Unlike FCI/Availability Groups, log shipping has **no
automatic failover** — an admin must promote a secondary and may need to reconfigure clients.
Characteristics:
- Redundancy for one primary and one or more secondaries.
- Limited read-only access to secondaries (requires special handling).
- Admin control over timing/delays of backups and restores; longer delays help recover from
  accidental data modification/deletion.

### Examples

Configure an Always On Availability Group:

```sql
CREATE DATABASE DB1;

ALTER DATABASE DB1 SET RECOVERY FULL;

BACKUP DATABASE DB1 TO DISK = N'\\MyBackupShare\DB1\DB1.bak' WITH FORMAT;

CREATE ENDPOINT DBHA STATE=STARTED
AS TCP (LISTENER_PORT=7022) FOR DATABASE_MIRRORING (ROLE=ALL);

CREATE AVAILABILITY GROUP AG_DB1
    FOR
        DATABASE DB1
    REPLICA ON
        'SecondarySQL' WITH
            (
            ENDPOINT_URL = 'TCP://secondarysql.example.com:7022',
            AVAILABILITY_MODE = ASYNCHRONOUS_COMMIT,
            FAILOVER_MODE = MANUAL
);

-- On SecondarySQL
ALTER AVAILABILITY GROUP AG_DB1 JOIN;

RESTORE DATABASE DB1 FROM DISK = N'\\MyBackupShare\DB1\DB1.bak'
WITH NORECOVERY;

-- On Primary
BACKUP LOG DB1
TO DISK = N'\\MyBackupShare\DB1\DB1_Tran.bak'
    WITH NOFORMAT

-- On SecondarySQL
RESTORE LOG DB1
    FROM DISK = N'\\MyBackupShare\DB1\DB1_Tran.bak'
    WITH NORECOVERY

ALTER DATABASE MyDb1 SET HADR AVAILABILITY GROUP = MyAG;
```

## MySQL

Aurora MySQL is a fully managed PaaS providing HA capabilities; RDS handles provisioning,
patching, backup, recovery, failure detection, and repair. New instances are always created
as part of a cluster (a single-node cluster if no replicas are specified); instances can be
added later.

### Regions and Availability Zones
RDS is hosted in multiple global locations composed of Regions and isolated Availability
Zones. Each Region is independent; AZs within a Region are connected by low-latency,
high-bandwidth links. By default resources aren't replicated across Regions. When creating an
instance you can specify an AZ or use **No preference**. Distribute instances across multiple
AZs so that if one AZ's instance fails, another takes over. Elastic IP addresses can abstract
instance failure by remapping the virtual IP to an instance in another AZ. An AZ is named by
a region code plus a letter (e.g., `us-east-1a`).

> Note: RDS independently maps AZs to identifiers per account, so `us-east-1a` may differ in
> physical location between accounts; AZs can't be coordinated across accounts.

### Aurora MySQL DB Cluster
A DB cluster consists of one or more DB instances plus a cluster volume (virtual storage
spanning multiple AZs, each holding a copy of the data). Instance types:
- **Primary instance** — supports read and write workloads; all DML transactions. Exactly one
  per cluster.
- **Aurora replica** — read-only. Zero to 15 replicas per cluster (max 16 instances total).
  Enable read scale-out; place across multiple AZs to increase availability.

### Endpoints
- **Cluster endpoint** — connects to the current primary regardless of AZ; one per cluster.
  Use for all writes (DML and DDL) and for transparent failover. On primary failure, Aurora
  fails over automatically. Example:
  `mydbcluster.cluster-123456789012.us-east-1.rds.amazonaws.com:3306`
- **Reader endpoint** — connects to a read-only replica; one per cluster. Load-balances
  read-only *connections* (not specific queries/workloads) across replicas; redirects to the
  primary if no replicas exist. Example:
  `mydbcluster.cluster-ro-123456789012.us-east-1.rds.amazonaws.com:3306`
- **Instance endpoint** — unique per instance. Use only when the application handles failover
  and read scale-out itself. Example:
  `mydbinstance.123456789012.us-east-1.rds.amazonaws.com:3306`

General considerations: prefer the cluster endpoint for HA (auto-redirects to the new primary
on failover); with instance endpoints you must discover roles via the console/API; the reader
endpoint balances connections but not individual queries — use instance endpoints for custom
read-distribution rules; the reader endpoint may redirect to the primary during a replica
promotion.

### Amazon Aurora Storage
Data is stored in a single virtual cluster volume on SSDs, comprising multiple copies
distributed across AZs in a Region — minimizing data loss and enabling failover. Cluster
volumes auto-grow up to 64 TiB; max table size is therefore also 64 TiB.

### Storage Auto-Repair
Aurora maintains multiple data copies across three AZs. It detects disk failures and
automatically repairs failed segments using data from other copies, greatly reducing data
loss and restore needs.

### Survivable Cache Warming
On instance start, Aurora pre-loads the buffer pool with frequently used pages. The cache is
managed by a separate process that survives database restarts, so the instance starts with a
warm buffer pool.

### Crash Recovery
Aurora MySQL recovers from a crash almost instantly, performing recovery asynchronously with
parallel threads so the database stays open and available immediately after a crash.

### Delayed Replication
> Note: RDS for MySQL supports delayed replication — a configurable lag for a read replica.
> Useful for DR/human error: if a table is accidentally dropped, stop replication just before
> that point and promote the replica to standalone. A stored procedure stops replication once
> a specified binary-log point is reached. Available in MySQL 5.7.22+ and 5.6.40+ in all
> Regions; configured via stored procedure at replica creation or for an existing replica.

### Examples

Two options for an additional reader instance:

| Read instance option | Description | Usage |
|---|---|---|
| Reader | Another reader instance in the same Region | Lower cost and latency between instances |
| Cross-region read replica | A reader instance in another Region | Better for DR plans requiring distance between primary and standby |

**To create a cross-region read replica:** RDS console → select instance → **Instance
actions** → **Create cross-region read replica** → enter details → **Create**.

**To create a read replica in the same region:** RDS console → select instance → **Instance
actions** → **Add reader** → enter details → **Create**.

After creation, run reads/writes on the primary and read-only operations on the replica.

## Conversion notes

| Feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Server-level failure protection | Failover Cluster Instances | N/A | Clustering handled by Aurora MySQL |
| Database-level failure protection | Always On Availability Groups | Amazon Aurora Replicas | |
| Log replication | Log Shipping | N/A | Aurora handles data replication at the storage level |
| Disk error protection | `RESTORE… PAGE=` | Automatic | |
| Maximum read-only replicas | 8 + Primary | 15 + Primary | |
| Failover address | Availability group listener | Cluster endpoint | |
| Read-only workloads | `READ INTENT` connection | Reader endpoint | |

- Aurora MySQL replaces SQL Server's WSFC/FCI/Availability Group/Log Shipping stack with a
  managed multi-AZ cluster: storage-level replication across three AZs, automatic storage
  auto-repair, near-instant crash recovery, and transparent failover via the cluster endpoint.
- Up to 15 Aurora replicas (vs. 8 SQL Server secondaries) for read scale-out, addressable via
  the reader endpoint.
