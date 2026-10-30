# Amazon Aurora Parallel Query

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tools.parallelquery.html

**Conversion category:** N/A (Aurora MySQL performance feature)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Replaced Aurora MySQL 2 limits with the current version 3 / 8.4 ones (partitioned tables, LOB/JSON columns and DYNAMIC row format now work; not with I/O-Optimized or t2/t3); verified it is off by default on both; zero-ETL alternative.

## Overview

Amazon Aurora Parallel Query is a feature of Amazon Aurora that provides faster analytical queries over current data without copying it into a separate system. It can speed up queries by up to **two orders of magnitude** ([AWS: Parallel Query for Amazon Aurora](https://aws.amazon.com/rds/aurora/parallel-query/)) while maintaining high throughput for the core transactional workload.

Unlike databases that parallelize across CPUs in one or a few servers, Parallel Query takes advantage of Aurora's unique architecture to push down and parallelize query processing across **thousands of CPUs in the Aurora storage layer**. Offloading analytical processing to the storage layer reduces network, CPU, and buffer pool contention with the transactional workload.

## Features

**Accelerate your analytical queries** — In a traditional database, running analytics directly means slower performance and risk of slowing the transactional workload. Queries can run minutes to hours depending on table and instance size, and are slowed by network latency when the storage layer transfers entire tables to the database server. With Parallel Query, processing is pushed down to the Aurora storage layer: the query gains large computing power and transfers far less data over the network, so the database instance keeps serving transactions with much less interruption — running transactional and analytical workloads side by side at high performance.

**Query on fresh data** — Operational systems (network monitoring, cyber-security, fraud detection) need fresh, real-time data and can't wait for extraction to an analytics system. Running queries in the same transaction-processing database (without degrading transaction performance) enables smarter operational decisions with no additional software and no query changes.

## Benefits

- **Improved I/O performance** — Parallelizes physical read requests across multiple storage nodes.
- **Reduced network traffic** — Aurora transmits compact tuples containing only the column values needed for the result set, instead of entire data pages that are filtered afterward.
- **Reduced CPU usage on the head node** — Pushes down function processing, row filtering, and column projection for the `WHERE` clause.
- **Reduced memory pressure on the buffer pool** — Pages processed by Parallel Query aren't added to the buffer pool, reducing the chance a data-intensive scan evicts frequently used data.
- **Potentially reduced data duplication in ETL pipelines** — Makes it practical to run long-running analytic queries on existing data.

## Important notes / limitations

Current limitations for Aurora MySQL 3 and 8.4 ([AWS docs](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-mysql-parallel-query.html), checked 2026-10-29). The original playbook listed Aurora MySQL 2 limits, most of which are gone:
- **Row format** — `COMPACT` or `DYNAMIC` (the MySQL 8 default) work; `COMPRESSED` and `REDUNDANT` don't.
- **Partitioned tables** — supported in version 3 / 8.4; each partition must be large enough to qualify, so fewer, larger partitions are more likely to use it.
- **Data types** — `TEXT`, `BLOB`, `JSON`, `GEOMETRY` and long `VARCHAR`/`CHAR` columns are supported in version 3 / 8.4 (extra retrieval overhead).
- **DDL** — can run alongside instant DDL in version 3 / 8.4.
- **Not supported** with the **Aurora I/O-Optimized** storage configuration, or on `db.t2`/`db.t3` instance classes.
- **Off by default** — `aurora_parallel_query` = 0 on both 3.13 and 8.4.8 (verified); turn it on in the cluster parameter group or per session.
- **Cost** — no feature charge, but parallel query bypasses the buffer pool, so `VolumeReadIOPS` and I/O charges go up. Prefer running it on reader instances.

See: Amazon Aurora Parallel Query (https://aws.amazon.com/rds/aurora/parallel-query/).

## Conversion notes

- Relevant for migrated Oracle workloads that mixed OLTP with reporting/analytics — Parallel Query can replace some Oracle features used for analytics (e.g., Oracle parallel query/parallel execution) directly on the Aurora MySQL target.
- A possible alternative to building a separate analytics system or heavy ETL after migration.
- Mind the constraints: not with I/O-Optimized storage or burstable instance classes; `COMPRESSED`/`REDUNDANT` row formats are excluded. Confirm with `EXPLAIN` ("Using parallel query") on production-sized data.
- For heavy analytics consider an Aurora zero-ETL integration to Amazon Redshift instead (supported on both 3.x and 8.4).
- No feature charge, but watch for increased I/O cost due to direct storage access.
