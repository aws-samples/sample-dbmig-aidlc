# Oracle Traffic Director and Amazon RDS Proxy for Amazon Aurora PostgreSQL

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.hadr.traffic.html

**Conversion category:** Manual (Two-star feature compatibility — some features may be replaced by Amazon RDS Proxy)
**SCT automation:** No automation

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): added version-support check, session pinning caveats for converted code, and AWS Advanced wrappers / PgBouncer alternatives.

## Oracle

Starting with Oracle 18c, Oracle Connection Manager can be configured to run in **Traffic Director mode**. Oracle Traffic Director is a fast, reliable load-balancing solution. Enabling it for Oracle Connection Manager (CMAN) provides:
- Increased scalability through transparent connection load-balancing.
- Zero-downtime high availability, including support for planned database maintenance, pluggable database relocation, and unplanned database outages for read-mostly workloads.
- High availability of Connection Manager (CMAN), avoiding a single point of failure.
- Security features: database proxy, firewall, tenant isolation in multi-tenant environments, DDOS protection, and database traffic secure tunneling.

See: [Configuring Oracle Connection Manager in Traffic Director Mode](https://docs.oracle.com/en/database/oracle/oracle-database/18/netag/configuring-oracle-connection-manager.html).

## PostgreSQL

Oracle Traffic Director mode for Connection Manager can potentially be replaced by **Amazon RDS Proxy** when migrating to Aurora PostgreSQL.

RDS Proxy simplifies connection management for Amazon RDS DB instances and clusters. It handles network traffic between the client application and the database actively — first understanding the database protocol, then adjusting its behavior based on the SQL operations from the application and the result sets from the database.

Benefits:
- Reduces memory and CPU overhead for database connection management. The database needs fewer resources when applications open many simultaneous connections.
- Does not require applications to close/reopen long-idle connections; requires less application logic to reestablish connections after a database problem.
- Highly available infrastructure deployed over multiple Availability Zones.
- Compute, memory, and storage are independent of the RDS DB instances and Aurora clusters — lowering overhead on database servers so they can devote resources to workloads.
- Compute resources are **serverless**, automatically scaling based on database workload.

See: [Amazon RDS Proxy](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html).

## Conversion notes

- This is an infrastructure/service mapping rather than a code conversion — there is no direct SQL/syntax translation. Conversion is manual with no automation.
- Oracle Traffic Director (CMAN Traffic Director mode) → Amazon RDS Proxy is a functional, not feature-for-feature, replacement. Some Oracle features (firewall, tenant isolation, DDOS protection, secure tunneling) are not part of RDS Proxy's scope and may need other AWS services (e.g., security groups, VPC, network ACLs) or be dropped.
- RDS Proxy's core value for migration: connection pooling/multiplexing, reduced DB connection overhead, improved failover handling, and serverless auto-scaling across AZs.
- Check the RDS Proxy supported-engines page for your Aurora PostgreSQL major version before you design around it. Support for a new major version can trail the engine's release.
- **Session pinning**: session-level state (`SET` outside a transaction, temporary tables, advisory locks, prepared statements in some drivers) pins a client to one database connection and removes the multiplexing benefit. Converted code that relies on session state (former package variables, global temporary tables) needs review before it goes behind RDS Proxy.
- Alternatives and complements: the **AWS Advanced JDBC / Python / Node.js wrappers** (topology-aware fast failover, IAM and Secrets Manager auth) and self-managed **PgBouncer** on EC2/ECS. Use reader endpoints or proxy read-only endpoints for read scaling.
