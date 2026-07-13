# Migrate to Aurora MySQL Serverless

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.hadr.serverless.html

**Conversion category:** N/A (infrastructure / deployment-option topic)
**SCT automation:** N/A

## Oracle

(No direct Oracle feature equivalent.) The playbook positions Aurora Serverless as a cost-efficient alternative to running Oracle RAC for infrequent, intermittent, or unpredictable workloads — you avoid managing/provisioning fixed cluster hardware and avoid paying for unused capacity.

## MySQL

Amazon Aurora Serverless is an on-demand, auto-scaling configuration for Aurora MySQL-compatible edition. The database automatically starts up, shuts down, and scales capacity up or down based on application needs — no instances to manage. (At the time of writing, the playbook notes this option is available only with Aurora MySQL 5.6 compatible.)

You create a database endpoint, optionally specify a capacity range, and connect your application. You pay per-second for capacity used while the database is active, and can migrate between standard and serverless configurations from the Amazon RDS console.

Set minimum and maximum capacity units; the instance scales in/out automatically with workload. Capacity unit options:

| CPU | RAM |
|---|---|
| 2 | 4 GB |
| 4 | 8 GB |
| 8 | 16 GB |
| 16 | 32 GB |
| 32 | 64 GB |
| 64 | 122 GB |
| 128 | 244 GB |
| 256 | 488 GB |

### How it works
- Creates an Aurora storage volume replicated across multiple AZs.
- Creates an endpoint in your VPC for the application to connect to.
- Places an (invisible) network load balancer behind that endpoint.
- Uses multi-tenant request routers to route DB traffic to the underlying instances.
- Provisions the initial minimum instance capacity.

Easier than Oracle RAC: no adding/removing cluster servers, no spend on unused hardware, and it can scale beyond the capacity you originally anticipated.

See [Amazon Aurora Serverless](https://aws.amazon.com/rds/aurora/serverless/).

## Conversion notes
- Deployment-model choice, not a schema/code conversion — no SCT automation.
- Best fit for infrequent, intermittent, or unpredictable workloads; for steady high-throughput OLTP, provisioned Aurora is usually more appropriate.
- The playbook cites Aurora MySQL 5.6 compatibility for Serverless v1; verify current Aurora Serverless v2 capabilities and supported engine versions against current AWS documentation before designing for it.
- Capacity is expressed in ACUs (the CPU/RAM pairs above for v1); v2 uses finer-grained ACU scaling.
