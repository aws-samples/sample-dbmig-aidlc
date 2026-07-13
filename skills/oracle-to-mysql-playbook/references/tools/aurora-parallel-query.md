# Amazon Aurora Parallel Query

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tools.parallelquery.html

**Conversion category:** N/A (Aurora MySQL performance feature)
**SCT automation:** N/A

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

- **Table formats** — The table row format must be `COMPACT`; partitioned tables aren't supported.
- **Data types** — `TEXT`, `BLOB`, and `GEOMETRY` data types aren't supported.
- **DDL** — The table can't have any pending fast online DDL operations.
- **Cost** — Available at no extra charge, but because it makes direct access to storage, your I/O cost may increase.

See: Amazon Aurora Parallel Query (https://aws.amazon.com/rds/aurora/parallel-query/).

## Conversion notes

- Relevant for migrated Oracle workloads that mixed OLTP with reporting/analytics — Parallel Query can replace some Oracle features used for analytics (e.g., Oracle parallel query/parallel execution) directly on the Aurora MySQL target.
- A possible alternative to building a separate analytics system or heavy ETL after migration.
- Mind the constraints: `COMPACT` row format only, no partitioned tables, and no `TEXT`/`BLOB`/`GEOMETRY` columns — verify candidate tables qualify.
- No feature charge, but watch for increased I/O cost due to direct storage access.
