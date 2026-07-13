# Amazon RDS on Outposts

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tools.rdsoutposts.html

**Conversion category:** N/A (deployment option / service)
**SCT automation:** N/A

> **Note:** This topic relates to Amazon RDS and is **not** supported with Amazon Aurora.

## Overview

Amazon RDS on Outposts is a fully managed service that offers the same AWS infrastructure, AWS services, APIs, and tools in virtually any data center, co-location space, or on-premises facility, for a consistent hybrid experience. It is ideal for workloads that require:

- Low-latency access to on-premises systems.
- Local data processing.
- Data residency.
- Migration of applications with local system inter-dependencies.

When deployed, you can run Amazon RDS on premises for low-latency workloads that need to run close to your on-premises data and applications. It also enables automatic backup to an AWS Region. You manage RDS databases both in the cloud and on premises using the same AWS Management Console, APIs, and CLI.

Supported database engines: **Microsoft SQL Server, MySQL, and PostgreSQL** (more coming soon).

## How it works

You deploy and scale an Amazon RDS DB instance in Outposts just as you do in the cloud — using the AWS Management Console, APIs, or CLI. RDS databases in Outposts are:

- Encrypted at rest using AWS KMS keys.
- Backed up automatically; all automatic backups and manual snapshots are stored in the AWS Region.

This option helps when you need to run Amazon RDS on premises for low-latency workloads that must run in close proximity to your on-premises data and applications.

See: AWS Outposts Family, Amazon RDS on Outposts, and "Create Amazon RDS DB Instances on Outposts".

## Conversion notes

- **Not applicable to Aurora** — Aurora MySQL clusters cannot run on Outposts; this is an RDS-only deployment option. If your target is Aurora MySQL, this service does not apply.
- Relevant only when data residency, very low latency to on-premises apps, or local inter-dependencies force an on-premises footprint while still wanting managed RDS (SQL Server / MySQL / PostgreSQL).
- Backups/snapshots are stored in the parent AWS Region (not purely local), which has data-residency implications to consider.
