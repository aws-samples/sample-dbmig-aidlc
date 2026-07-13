# Oracle Real Application Clusters (RAC) and PostgreSQL Aurora Architecture

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.hadr.rac.html

**Conversion category:** Manual (Three-star feature compatibility — distribute load/applications/users across multiple instances)
**SCT automation:** N/A

## Oracle

Oracle Real Application Clusters (RAC) allows multiple Oracle instances to access a single database, providing highly available and scalable relational databases in **Active-Active** mode. Applications can access the database through multiple instances simultaneously.

RAC requires network configuration of SCAN IPs, VIP IPs, interconnect, and more. As a best practice all servers run the same Oracle software versions.

Because all nodes write to a single shared set of database data files on disk, two coordination mechanisms ensure ACID compliance:
- **GCS (Global Cache Services)** — tracks location/status of database data blocks; guarantees data integrity for global access across nodes.
- **GES (Global Enqueue Services)** — performs concurrency control across nodes including cache locks and transactions.

These run as background processes on each node and serialize access to shared data structures.

**Shared storage** is essential — all nodes read/write the same physical files on disk accessible by all nodes. Many customers use high-end storage hardware. Oracle also provides **Automatic Storage Management (ASM)**, a software-based storage/disk management mechanism implemented as background processes on all nodes.

### Performance and scale-out with Oracle RAC
- You can add nodes to an existing cluster without downtime, increasing HA and performance.
- **Read scaling** is easy by adding nodes. **Write scaling** is more complex: multiple sessions modifying rows in the same physical Oracle block cause write overhead and impact write performance.
- RAC uses a "smart mastering" mechanism to reduce write-concurrency overhead — the database masters data blocks only on nodes where the relevant service is active.
- Many customers split RAC clusters into multiple **services** (logical node groupings) to direct writes to specific nodes:
  - **Application partitioning** — splitting writes from different application modules (groups of independent tables) to different nodes.
  - For highly concurrent non-optimized workloads — directing all writes to a single node and load-balancing only reads.

Two major RAC benefits:
- Multiple nodes provide increased HA (no single point of failure from DB servers), though shared storage requires its own storage-based HA/DR solution.
- Multiple nodes enable scaling-out query performance across servers.

## PostgreSQL

Aurora extends vanilla PostgreSQL in two major ways:
- Kernel enhancements to improve performance (concurrency, locking, multi-threading).
- Uses AWS services for greater HA, DR, and backup/recovery functionality.

Key architectural difference vs RAC: instead of multiple read/write nodes accessing shared disk, an Aurora cluster has a **single primary node** (reads + writes) and a set of **replica nodes** (reads only) with automatic promotion to primary on failure. While RAC coordinates writes across all nodes via background processes, the Aurora primary writes a constant **redo stream** to six storage nodes distributed across three Availability Zones. **Only redo log records cross the network — not pages.**

Each Aurora cluster can have:
- A single **primary** instance handling writes and reads.
- Up to **15 read replicas** used for:
  - **Performance and Read Scalability** — read-only nodes for queries/reports.
  - **High Availability** — failover nodes; each replica can be in one of the three AZs (an AZ can host more than one replica).

Aurora storage: a volume made of **10 GB segments** with **six copies** across three AZs. Each read replica shares the same underlying volume as the primary. Promotion of a replica to primary usually occurs in **less than 30 seconds with no data loss**.

For a write to be durable, the primary sends a redo stream to six storage nodes (two per AZ) and waits until **four of six** respond. No database pages are written from the database tier to the storage tier; the storage volume asynchronously applies redo records to generate pages in the background or on demand.

### High availability and scale-out in Aurora
Two endpoints:
- **Cluster Endpoint** — connects to the current primary instance (read + write). On primary failure, Aurora automatically fails over to a new primary; the cluster endpoint continues serving with minimal interruption.
- **Reader Endpoint** — provides round-robin load balancing across replicas to scale out reads. Enhances HA: if an AZ fails, read traffic continues to other replicas with minimal disruption.

Aurora focuses on scale-out of reads (RAC scales out both reads and writes), but most OLTP applications are not limited by write scalability. Many RAC customers use RAC primarily for HA and secondarily to scale out reads.

## Conversion notes

| Feature | Oracle RAC | Amazon Aurora |
|---|---|---|
| Storage | Enterprise-grade storage + ASM | Distributed, low-latency storage engine spanning multiple AZs |
| Cluster type | Active/Active — all nodes open for R/W | Active/Active — primary open for R/W, replicas open for reads |
| Cluster virtual IPs | R/W load balancing: SCAN IP | R/W: Cluster endpoint + Read load balancing: Reader endpoint |
| Internode coordination | Cache-fusion + GCS + GES | N/A |
| Internode private network | Interconnect | N/A |
| Transaction (write) TTR from node failure | Typically 0–30 seconds | Typically less than 30 seconds |
| Application (read) TTR from node failure | Immediate | Immediate |
| Max cluster nodes | Theoretical max 100 (2–10 common) | 15 |
| Built-in read scaling | Yes | Yes |
| Built-in write scaling | Yes (limited when sessions modify rows in same blocks) | No |
| Data loss on node failure | No data loss | No data loss |
| Replication latency | N/A | Milliseconds |
| Operational complexity | Requires DB, IT, network, storage expertise | Provided as a cloud solution |
| Scale-up nodes | Difficult with physical hardware (replace servers) | Easy via AWS UI/CLI |
| Scale-out cluster | Provision/deploy/configure new servers | Easy via AWS UI/CLI |

- Aurora is a simplified Oracle RAC alternative for typical OLTP applications needing high-performance writes, scalable reads, and very high availability with lower operational overhead.
- Aurora cluster spans three AZs ("stretch" cluster) for strong HA and durability; storage is automatically added as needed and you pay for one copy of your data.
- See: [Amazon Aurora as an Alternative to Oracle RAC](https://aws.amazon.com/blogs/database/amazon-aurora-as-an-alternative-to-oracle-rac).
