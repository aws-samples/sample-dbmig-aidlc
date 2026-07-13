# Oracle Real Application Clusters and Aurora MySQL architecture

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.hadr.rac.html

**Conversion category:** N/A (infrastructure / HA topic — three-star feature compatibility)
**SCT automation:** N/A

## Oracle

Oracle Real Application Clusters (RAC) lets multiple Oracle instances access a single database in Active-Active mode, providing high availability, scalability, and load balancing.

RAC requires network configuration of SCAN IPs, VIP IPs, interconnect, and related items. Best practice: all servers run the same Oracle software version.

Because all nodes write to a single shared set of data files, two coordination mechanisms maintain ACID compliance:
- **Global Cache Services (GCS)** — tracks location/status of data blocks; guarantees integrity for global access across nodes.
- **Global Enqueue Services (GES)** — concurrency control across nodes (cache locks and transactions).

These run as background processes on each node to serialize access to shared structures.

**Shared storage** is essential — all nodes read/write the same physical files on shared disk. Customers typically use high-end storage hardware, or Oracle's software-based **Automatic Storage Management (ASM)**.

Performance and scale-out:
- Add nodes without downtime to increase HA and performance.
- Read scaling is easy; **write scaling is more complicated** — multiple sessions modifying rows in the same physical block cause write overhead.
- RAC uses a "smart mastering" mechanism to reduce write-concurrency overhead, mastering data blocks only on nodes where the relevant service is active.
- Many customers split clusters into **services** (logical node groupings) for application partitioning, or direct all writes to one node and load-balance only reads.

Two major benefits:
- Multiple nodes provide HA (no single point of failure on the DB servers; shared storage still needs its own HA/DR).
- Multiple nodes scale out query performance.

See [Oracle Real Application Clusters](https://docs.oracle.com/en/database/oracle/oracle-database/19/racad/index.html).

## MySQL

Aurora extends vanilla MySQL by (1) enhancing the kernel for performance (concurrency, locking, multi-threading) and (2) using AWS services for HA, DR, and backup/recovery.

Architectural difference vs RAC: instead of multiple read/write nodes on shared disk, an Aurora cluster has **a single primary** (reads + writes) and a set of **read replicas** (reads, with automatic promotion on failure). The primary writes a constant redo stream to **six storage nodes across three AZs** — only redo log records cross the network, never pages.

Each cluster can have:
- One primary handling writes and reads.
- Up to **15 read replicas**, used for read scalability and HA (failover nodes, each in any of the three AZs).

Storage: the Aurora volume is made of 10 GB segments, six copies across three AZs. Replicas share the same underlying volume as the primary. Replica promotion usually completes in **under 30 seconds with no data loss**. For a durable write, the primary sends redo to six storage nodes (two per AZ) and waits for four of six to acknowledge. No database pages are written from the DB tier to the storage tier; the storage volume applies redo to generate pages asynchronously.

### High availability and scale-out endpoints

- **Cluster endpoint** — connects to the current primary for reads and writes; on failover, Aurora redirects this endpoint to the new primary with minimal interruption.
- **Reader endpoint** — round-robin load balancing across replicas for read scale-out; if an AZ fails, read traffic continues to other replicas.

While Aurora scales out reads (not writes) and RAC can scale both, most OLTP workloads are not limited by write scalability — many RAC customers adopt RAC primarily for HA and secondarily for read scale-out.

### Summary comparison

| Feature | Oracle RAC | Amazon Aurora |
|---|---|---|
| Storage | Enterprise storage + ASM | Distributed low-latency storage nodes spanning multiple AZs |
| Cluster type | Active/Active, all nodes R/W | Active/Active, primary R/W, replicas read-only |
| Cluster virtual IPs | SCAN IP (R/W load balancing) | Cluster endpoint (R/W) + Reader endpoint (read LB) |
| Internode coordination | Cache-fusion + GCS + GES | N/A |
| Internode private network | Interconnect | N/A |
| Write TTR from node failure | ~0–30 seconds | Typically < 30 seconds |
| Read TTR from node failure | Immediate | Immediate |
| Max cluster nodes | Theoretical 100 (2–10 common) | 15 |
| Built-in read scaling | Yes | Yes |
| Built-in write scaling | Yes (limited under same-block contention) | No |
| Data loss on node failure | None | None |
| Replication latency | N/A | Milliseconds |
| Operational complexity | DB/IT/network/storage expertise | Managed cloud solution |
| Scale-up nodes | Hard (replace servers) | Easy (AWS UI/CLI) |
| Scale-out cluster | Provision/deploy new servers | Easy (AWS UI/CLI) |

## Conversion notes
- No automated conversion path — RAC is replaced by Aurora's managed cluster architecture, a re-architecture decision, not a code translation.
- Aurora cannot scale out writes the way RAC theoretically can; confirm the workload is read-scaling-bound (true for most OLTP) before treating Aurora as a drop-in RAC replacement.
- RAC concepts with no Aurora equivalent: GCS/GES cache fusion, interconnect, SCAN IP, ASM. Map SCAN IP → cluster endpoint, read load balancing → reader endpoint.
- Aurora reduces operational overhead (automatic storage growth, managed failover) and total cost of ownership.
- See [Amazon Aurora as an Alternative to Oracle RAC](https://aws.amazon.com/blogs/database/amazon-aurora-as-an-alternative-to-oracle-rac).
