# Amazon Aurora Parallel Query Overview

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.parallelquery.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A — Aurora MySQL performance feature.

## SQL Server
N/A on the source side. Conceptually comparable to SQL Server's parallel query execution, but Aurora pushes processing down to the distributed storage layer rather than parallelizing across a few server CPUs.

## MySQL
Aurora Parallel Query is an Aurora MySQL feature for faster analytical queries over current data without copying it into a separate system. It can speed up queries by up to two orders of magnitude ([AWS: Parallel Query for Amazon Aurora](https://aws.amazon.com/rds/aurora/parallel-query/)) while maintaining high throughput for transactional workloads, by pushing down and parallelizing query processing across thousands of CPUs in the Aurora storage layer.

## Conversion notes
### Features
- **Accelerate analytical queries:** Pushes query processing down to the storage layer; the query gains large compute power and transfers far less data over the network. The DB instance keeps serving transactions with less interruption — run transactional + analytical workloads together with high performance.
- **Query on fresh data:** Run analytics in the same transactional database (no ETL extract delay), enabling smarter operational decisions with no extra software and no query changes. Good for network monitoring, cyber-security, fraud detection.

### Benefits
- Improved I/O performance by parallelizing physical read requests across multiple storage nodes.
- Reduced network traffic — Aurora transmits compact tuples with only needed column values, not entire data pages.
- Reduced CPU usage on the head node by pushing down function processing, row filtering, and column projection for the `WHERE` clause.
- Reduced buffer pool memory pressure — pages processed by parallel query aren't added to the buffer pool, avoiding eviction of frequently used data.
- Potentially reduced data duplication in ETL pipelines by making long-running analytic queries on existing data practical.

### Important notes / limitations
- **Table formats:** Row format must be `COMPACT`; partitioned tables are **not** supported.
- **Data types:** `TEXT`, `BLOB`, and `GEOMETRY` are **not** supported.
- **DDL:** The table can't have pending fast online DDL operations.
- **Cost:** Available at no extra charge, but because it accesses storage directly, IO cost may increase.
