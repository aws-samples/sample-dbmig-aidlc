# Amazon RDS Proxy

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tools.rdsproxy.html

**Conversion category:** N/A (connection-management service)
**SCT automation:** N/A

## Oracle
Not an Oracle feature. Conceptually comparable to connection-pooling middleware used in front of Oracle (e.g., application-side pools), but RDS Proxy is a fully managed AWS service.

## PostgreSQL
Amazon RDS Proxy is a fully managed, highly available database proxy for Amazon RDS that makes applications more scalable, more resilient to database failures, and more secure. It is generally available for **Aurora MySQL, Aurora PostgreSQL, Amazon RDS for MySQL, and Amazon RDS for PostgreSQL**.

Applications (especially serverless) that open/close many connections at a high rate can exhaust database memory and compute. RDS Proxy lets applications **pool and share** connections, improving efficiency and scalability. It reduces failover times for Aurora and RDS by up to **66%**, and integrates with **AWS Secrets Manager** and **AWS IAM** for credential, authentication, and access management.

Can be enabled for most applications with **no code changes**; no additional infrastructure to provision or manage. Pricing is per vCPU of the database instance for which the proxy is enabled.

**Benefits:**
- **Improved performance** — connection pooling reduces stress on DB compute/memory from frequent new connections; supports large numbers/frequency of connections.
- **Increased availability** — automatically connects to a new DB instance while preserving application connections, cutting failover time by ~66%.
- **Managed security** — centrally manage DB credentials via AWS Secrets Manager.
- **Fully managed** — no patching/managing your own proxy server.
- **Fully compatible** — speaks the supported engines' native protocols; no application code changes.
- **Available and durable** — deployed across multiple Availability Zones to protect against infrastructure failure.

## Conversion notes
- Useful post-migration to handle connection storms from serverless or high-concurrency apps hitting Aurora/RDS PostgreSQL.
- Pairs well with **Aurora Serverless** workloads and with **AWS Secrets Manager / IAM** authentication.
- No application code changes typically required to adopt.
- See: "Amazon RDS Proxy for Scalable Serverless Applications" and the Amazon RDS Proxy product page.
