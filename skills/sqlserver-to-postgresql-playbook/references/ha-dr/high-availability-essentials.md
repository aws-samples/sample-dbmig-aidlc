# High Availability Essentials

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.hadr.essentials.html

**Conversion category:** N/A (infrastructure / managed-service topic) — multi-replica, scale-out solution using Aurora clusters and Availability Zones
**SCT automation:** N/A

## SQL Server

SQL Server offers several HA/DR solutions: Always On Failover Cluster Instances (FCI), Always On Availability Groups, Database Mirroring, and Log Shipping. SQL Server 2017 added read-scale availability groups without a cluster, the Minimum Replica Commit setting, and cross-OS (Windows–Linux) support. SQL Server 2019 added database snapshots of memory-optimized filegroups and secondary-to-primary read/write connection redirection for Always On AGs.

### Always On Failover Cluster Instances (FCI)
Uses Windows Server Failover Clustering (WSFC) to deliver redundancy at the **server instance level**. An FCI is a SQL Server instance installed across two or more WSFC nodes; it appears as a single normal instance to clients. On failure of the active node, ownership of the resource group transfers to another node transparently. Benefits:
- Full instance-level protection.
- Automatic failover of resources between nodes.
- Wide storage support (iSCSI, Fiber Channel, SMB file shares, etc.).
- Multi-subnet support.
- No client reconfiguration after failover.
- Configurable failover policies; automatic health detection/monitoring.

### Always On Availability Groups
The most recent HA/DR solution (introduced in SQL Server 2012), configured at the **database level** (more control than FCI), also relying on WSFC. Uses real-time log delivery/apply to maintain near-real-time readable copies. Characteristics:
- Up to **nine availability replicas**: one primary + up to eight readable secondaries.
- Asynchronous-commit and synchronous-commit modes.
- Automatic, manual, and forced failover (only forced can lose data).
- Secondary replicas allow read-only access and backup offloading.
- **Availability Group Listener** — a virtual server address; routes read-only requests to readable replicas and read-write to primary, enabling fast failover without client reconfiguration.
- Flexible failover policies; automatic page repair against corruption.
- Encrypted, compressed log transport.
- Rich tooling (T-SQL DDL, SSMS wizards, Always On Dashboard, PowerShell).

### Database Mirroring
Legacy, **deprecated** (Microsoft recommends Always On AGs instead). Near-instant failover, but only one database at a time with a single standby replica.

### Log Shipping
One of the oldest, well-tested solutions, configured at the database level. Three steps:
1. Back up the transaction log of the primary.
2. Copy the log backup to a secondary server.
3. Restore the log backup on the secondary.

Repeat steps 2–3 per secondary. **No automatic failover** — an administrator must promote the secondary and reconfigure clients. Characteristics: redundancy for one primary and one or more secondaries; limited read-only access to secondaries; admin control over timing/delays (longer delays can protect against accidental data changes).

### Example — configure an Always On Availability Group

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

## PostgreSQL

Aurora PostgreSQL is a fully managed PaaS. Amazon RDS handles provisioning, patching, backup, recovery, failure detection, and repair. Every new instance is created as part of a cluster — if no replicas are specified, a single-node cluster is created and you can add instances later.

### Regions and Availability Zones
RDS spans multiple Regions, each with multiple isolated Availability Zones (AZs) connected by low-latency, high-bandwidth links. Resources aren't replicated across Regions by default. Distribute instances across AZs so that if one AZ's instance fails, another AZ takes over. Elastic IPs can abstract instance failure by remapping the virtual IP. AZ identifiers (e.g., `us-east-1a`) are mapped independently per account.

### Aurora PostgreSQL DB Cluster
A cluster = one or more DB instances + a **cluster volume** (virtual storage spanning multiple AZs, each holding a copy of the data). Instance types:
- **Primary instance** — supports read and write; handles all DML/DDL. Exactly one per cluster.
- **Aurora Replica** — read-only; 0 to 15 per cluster (max 16 instances total). Enables read scale-out; place across AZs to increase availability.

### Endpoints
- **Cluster Endpoint** — connects to the current primary regardless of AZ; use for all writes (DML/DDL) and for transparent failover. On primary failure, Aurora automatically fails over to a new primary. Example: `mydbcluster.cluster-123456789012.us-east-1.rds.amazonaws.com:3306`.
- **Reader Endpoint** — connects to one of the read replicas; load-balances read-only *connections* (not individual queries/workloads). Falls back to the primary if no replicas exist. Example: `mydbcluster.cluster-ro-123456789012.us-east-1.rds.amazonaws.com:3306`.
- **Instance Endpoint** — unique per instance; use only when the application handles failover and read scale-out itself. Example: `pgsdbinstance.123456789012.us-east-1.rds.amazonaws.com:3306`.

Considerations: prefer the cluster endpoint for HA (auto-redirects to new primary); use instance endpoints for custom read-distribution rules; the reader endpoint may temporarily redirect to the primary during a replica promotion.

### Amazon Aurora Storage
Data lives in a single virtual cluster volume on SSDs, with **multiple copies distributed across AZs**. The volume auto-grows up to a maximum of **64 TiB** (so the max table size is also 64 TiB).

### Storage Auto-Repair
Aurora maintains multiple data copies across **three AZs**. It detects disk-segment failures and repairs them automatically using data from other copies, greatly minimizing data loss and the need to restore.

### Survivable Cache Warming
On instance start, Aurora pre-loads the buffer pool with frequently used pages. The cache is managed by a separate process that survives database restarts, so the instance starts with a warm buffer pool.

### Crash Recovery
Aurora recovers from crashes near-instantly, performing recovery asynchronously with parallel threads so the database stays open and available immediately after a crash.

### Example — create a read replica (AWS Console)
1. AWS Console → **RDS**.
2. Select the instance → **Instance actions** → **Create cross-region read replica**.
3. Enter required details → **Create**.

After creation, run reads/writes on the primary and read-only operations on the replica.

## Conversion notes

- **Server-level failure protection (FCI)** has no equivalent — clustering is handled natively by Aurora PostgreSQL.
- **Database-level failure protection (Always On AGs)** maps to **Aurora Replicas**.
- **Log Shipping / log replication** has no equivalent — Aurora replicates data at the **storage level** across AZs automatically.
- **Disk error protection** — SQL Server uses `RESTORE … PAGE=`; Aurora does this **automatically** via storage auto-repair.
- **Maximum read-only replicas** — SQL Server: 8 + primary; Aurora: **15 + primary**.
- **Failover address** — SQL Server's Availability Group Listener maps to the Aurora **cluster endpoint**.
- **Read-only workloads** — SQL Server's `READ INTENT` connection maps to the Aurora **reader endpoint**.
- **Aurora HA specifics:** six-way replication across three AZs, automatic failover via cluster endpoint, survivable cache warming, near-instant parallel crash recovery, and a 64 TiB auto-growing cluster volume — HA is delivered by the managed service rather than configured DDL.
