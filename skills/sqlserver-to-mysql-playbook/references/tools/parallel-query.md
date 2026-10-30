# Amazon Aurora Parallel Query Overview

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.parallelquery.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A — Aurora MySQL performance feature.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Replaced Aurora MySQL 2 limits with the current 3 / 8.4 ones (partitioned tables, LOB/JSON, DYNAMIC; not with I/O-Optimized or t2/t3); verified off by default; MAXDOP and columnstore notes.

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
Current limits for Aurora MySQL 3 and 8.4 ([AWS docs](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-mysql-parallel-query.html), checked 2026-10-29); the original listed Aurora MySQL 2 limits:
- **Row format:** `COMPACT` or `DYNAMIC` (default) work; `COMPRESSED`/`REDUNDANT` don't.
- **Partitioned tables:** supported (larger partitions are more likely to qualify).
- **Data types:** `TEXT`, `BLOB`, `JSON`, `GEOMETRY` and long `VARCHAR` columns are supported (extra retrieval overhead).
- **DDL:** can run alongside instant DDL.
- **Not supported** with Aurora I/O-Optimized storage or `db.t2`/`db.t3` classes.
- **Off by default:** `aurora_parallel_query` = 0 on 3.13 and 8.4.8 (verified).
- **Cost:** no feature charge, but it bypasses the buffer pool, so read I/O charges rise; prefer readers.
- SQL Server `MAXDOP` / parallelism hints have no direct equivalent: Parallel Query is cost-based. For columnstore-style analytics consider a zero-ETL integration to Amazon Redshift.
