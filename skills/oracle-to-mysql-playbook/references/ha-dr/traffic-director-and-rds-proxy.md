# Oracle Traffic Director and Amazon RDS Proxy for Amazon Aurora MySQL

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.hadr.traffic.html

**Conversion category:** Manual (two-star feature compatibility; no automation — features may be replaced by Amazon RDS Proxy)
**SCT automation:** N/A (no automation)

## Oracle

Starting with Oracle 18c, **Oracle Connection Manager (CMAN)** can run in **Traffic Director mode** — a fast, reliable load-balancing solution. Enabling it provides:
- Increased scalability via transparent connection load balancing.
- Zero-downtime high availability: planned DB maintenance, pluggable database relocation, and unplanned outages for read-mostly workloads.
- High availability of CMAN itself (avoids a single point of failure).
- Security features: database proxy, firewall, tenant isolation in multi-tenant environments, DDoS protection, and secure tunneling of database traffic.

See [Configuring Oracle Connection Manager in Traffic Director Mode](https://docs.oracle.com/en/database/oracle/oracle-database/18/netag/configuring-oracle-connection-manager.html) in the Oracle documentation.

## MySQL

Oracle Traffic Director mode for Connection Manager can potentially be replaced by **Amazon RDS Proxy** when migrating to Aurora MySQL.

Amazon RDS Proxy simplifies connection management for RDS instances and Aurora clusters. It actively manages network traffic between client application and database: it understands the database protocol and adjusts behavior based on the SQL operations and result sets.

Benefits:
- Reduces database memory and CPU overhead from many simultaneous connections (pooling/multiplexing).
- Avoids requiring applications to close and reopen long-idle connections.
- Reduces application logic needed to reestablish connections after a database problem.
- Highly available, deployed across multiple AZs; compute/memory/storage are independent of the DB instances/cluster, so DB servers devote resources to workloads.
- Compute resources are serverless and scale automatically with database workload.

See [Amazon RDS Proxy](chap-oracle-aurora-mysql.tools.rdsproxy.html) and [Using Amazon RDS Proxy](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html) in the Amazon RDS user guide.

## Conversion notes
- No automated conversion — replacing CMAN/Traffic Director with RDS Proxy is a manual architectural substitution.
- RDS Proxy covers connection pooling, failover handling, and improved resilience; it does **not** replicate every CMAN feature (e.g., Oracle-specific firewall/tunneling/tenant-isolation capabilities). Evaluate which Traffic Director features are actually relied upon.
- RDS Proxy is most valuable for applications that open many short-lived connections or are sensitive to failover connection storms (e.g., serverless/Lambda fleets).
- IAM authentication and Secrets Manager integration are common RDS Proxy add-ons not present in the Oracle equivalent.
