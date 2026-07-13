# Amazon RDS Proxy

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tools.rdsproxy.html

**Conversion category:** N/A (managed service / post-migration architecture)
**SCT automation:** N/A

## Overview

Amazon RDS Proxy is a fully managed, highly available database proxy for Amazon RDS that makes applications more scalable, more resilient to database failures, and more secure.

Many applications — including modern serverless architectures — can have many open connections to the database and may open/close connections at a high rate, exhausting database memory and compute resources. RDS Proxy lets applications **pool and share** connections established with the database, improving efficiency and scalability. Fail-over times for Aurora and RDS databases are reduced by up to **66%**. You can manage database credentials, authentication, and access through integration with AWS Secrets Manager and AWS IAM.

RDS Proxy can be turned on for most applications with **no code changes** and no additional infrastructure to provision/manage. Pricing is per vCPU of the database instance for which the proxy is enabled. It is generally available for **Aurora MySQL, Aurora PostgreSQL, Amazon RDS for MySQL, and Amazon RDS for PostgreSQL**.

## Benefits

- **Improved application performance** — Manages a connection pool, reducing stress on database compute/memory that occurs when establishing new connections; efficiently supports a large number and frequency of application connections.
- **Increased application availability** — Automatically connects to a new database instance while preserving application connections, reducing fail-over time by 66%.
- **Manageable application security** — Centrally manage database credentials using AWS Secrets Manager.
- **Fully managed** — Proxy benefits without the burden of patching/managing your own proxy server.
- **Fully compatible with your database** — Compatible with supported engine protocols; deploy without application code changes.
- **Available and durable** — Highly available, deployed over multiple Availability Zones (AZs) to protect against infrastructure failure.

## How it works

RDS Proxy sits between the application and the database. Applications connect to the proxy endpoint instead of directly to the database; the proxy maintains a warm pool of connections and multiplexes application requests onto them, and reroutes connections to a healthy instance during failover.

See: "Amazon RDS Proxy for Scalable Serverless Applications" and "Amazon RDS Proxy".

## Conversion notes

- Especially valuable for Oracle→Aurora MySQL migrations where the application previously relied on Oracle connection pooling / shared servers, or for serverless/Lambda front ends that open many short-lived connections.
- Helps mitigate Aurora MySQL `max_connections` pressure without application changes.
- Reduces failover impact (up to 66% faster) — relevant for HA cutover planning.
- Use Secrets Manager + IAM integration to remove plaintext DB credentials from the application.
- Cost is per vCPU of the enabled database instance.
