# Amazon Aurora Serverless v1

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tools.auroraserverless.html

**Conversion category:** N/A (Aurora deployment / capacity option)
**SCT automation:** N/A

## Overview

Amazon Aurora Serverless v1 is an on-demand, autoscaling configuration for Amazon Aurora. An Aurora Serverless DB cluster scales compute capacity up and down based on application needs, in contrast to provisioned clusters where you manage capacity manually. It is a relatively simple, cost-effective option for infrequent, intermittent, or unpredictable workloads — it automatically starts up, scales compute to match usage, and shuts down when not in use.

The cluster volume is the same high-capacity, distributed, highly available storage used by provisioned clusters and is **always encrypted** (you can choose the key but can't turn off encryption).

### Advantages
- **Simpler than provisioned** — Removes much of the complexity of managing DB instances and capacity.
- **Scalable** — Seamlessly scales compute and memory with no disruption to client connections.
- **Cost-effective** — Pay only for database resources consumed, on a per-second basis.
- **Highly available storage** — Same fault-tolerant, distributed storage with six-way replication.

### Use cases
- **Infrequently used applications** (e.g., low-volume blog used a few minutes per day/week).
- **New applications** where the needed instance size is unknown.
- **Variable workloads** (e.g., HR, budgeting, operational reporting with short daily peaks).
- **Unpredictable workloads** with sudden spikes.
- **Development and test databases** used only during work hours.
- **Multi-tenant applications** — manages individual database capacity for each app in your fleet.

### Scaling behavior (v1)
Because storage is shared between nodes, Aurora can scale up or down in seconds for most workloads. Autoscaling thresholds: **1.5 minutes to scale up**, **5 minutes to scale down** (metrics must exceed/fall below limits for that duration to trigger). Cool-down between scaling activities: **5 minutes** to scale up, **15 minutes** to scale down. Scaling requires finding a "scaling point," which may take longer with long-running transactions. Scaling is transparent to connected clients (existing connections and session state transfer to new nodes). Pausing/resuming adds higher first-connection latency, typically ~25 seconds.

## Amazon Aurora Serverless v2

Aurora Serverless v2 is re-architected from the ground up for instantly scalable serverless clusters, on a lightweight foundation engineered for security and isolation in multitenant environments with very little overhead.

You define capacity as a range between minimum and maximum **Aurora capacity units (ACUs)**:
- **Minimum ACUs** — smallest number to which the cluster can scale down.
- **Maximum ACUs** — largest number to which the cluster can scale up.

Each ACU provides **2 GiB of memory (RAM)** plus associated vCPU and networking. Unlike v1 (which scales by **doubling** ACUs at each threshold), **v2 increases ACUs incrementally** to provide the best performance for resources consumed.

## How to provision

1. Sign in to the Management Console, choose **Amazon RDS**, then **Create database**.
2. Under **Engine options** → **Engine versions**, choose **Show versions that support Serverless v2**.
3. Choose the capacity settings for your use case.

See: Amazon Aurora Serverless; "Aurora Serverless MySQL Generally Available"; "Amazon Aurora PostgreSQL Serverless Now Generally Available".

## Conversion notes

- A capacity/deployment model for the Aurora MySQL target — not a schema-conversion concern.
- Good fit for migrated Oracle workloads that are intermittent or have unpredictable peaks; avoids provisioning for peak/average capacity.
- v1 scales by **doubling** ACUs with cool-down windows (slower, coarser); v2 scales **incrementally** and near-instantly — prefer v2 for production-like, latency-sensitive workloads.
- Storage is always encrypted (cannot be disabled) — factor into compliance planning.
- v1 pause/resume adds ~25s latency on the first connection after a pause; not ideal for latency-critical online workloads.
