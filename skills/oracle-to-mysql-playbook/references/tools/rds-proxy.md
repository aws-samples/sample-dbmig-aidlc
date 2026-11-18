# Amazon RDS Proxy

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tools.rdsproxy.html

**Conversion category:** N/A (managed service / post-migration architecture)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Version and auth-plugin check for 8.4, session-pinning caveat for converted package state, IAM and reader endpoints.

> **Content security review** (2026-11-18): the 66% failover figure now cites the RDS Proxy FAQs and the AWS Database Blog measurements.

## Overview

Amazon RDS Proxy is a fully managed, highly available database proxy for Amazon RDS that makes applications more scalable, more resilient to database failures, and more secure.

Many applications — including modern serverless architectures — can have many open connections to the database and may open/close connections at a high rate, exhausting database memory and compute resources. RDS Proxy lets applications **pool and share** connections established with the database, improving efficiency and scalability. RDS Proxy reduces failover times by up to **66%** for Amazon RDS and Aurora Multi-AZ databases, because it bypasses DNS caches and keeps application connections open while it connects to the new instance ([Amazon RDS Proxy FAQs](https://aws.amazon.com/rds/proxy/faqs/); measured client recovery times: [Improving application availability with Amazon RDS Proxy](https://aws.amazon.com/blogs/database/improving-application-availability-with-amazon-rds-proxy/)). You can manage database credentials, authentication, and access through integration with AWS Secrets Manager and AWS IAM.

RDS Proxy can be turned on for most applications with **no code changes** and no additional infrastructure to provision/manage. Pricing is per vCPU of the database instance for which the proxy is enabled. It is generally available for **Aurora MySQL, Aurora PostgreSQL, Amazon RDS for MySQL, and Amazon RDS for PostgreSQL**.

## Benefits

- **Improved application performance** — Manages a connection pool, reducing stress on database compute/memory that occurs when establishing new connections; efficiently supports a large number and frequency of application connections.
- **Increased application availability** — Automatically connects to a new database instance while preserving application connections, reducing failover time by up to 66% (see above).
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
- Reduces failover impact (up to 66% faster, per the [Amazon RDS Proxy FAQs](https://aws.amazon.com/rds/proxy/faqs/)) — relevant for HA cutover planning.
- Use Secrets Manager + IAM integration to remove plaintext DB credentials from the application.
- Cost is per vCPU of the enabled database instance (Serverless v2: per ACU).
- Confirm RDS Proxy supports the target major version (Aurora MySQL 8.4) on the RDS Proxy supported-engines page before go-live, and that client-to-proxy authentication supports `caching_sha2_password` users.
- Converted Oracle code that keeps **session state** — user variables emulating package globals, temporary tables, `SET` session variables, `GET_LOCK`, prepared statements — **pins** the client connection and removes most pooling benefit. Review it before putting the application behind the proxy.
- RDS Proxy supports IAM authentication and read-only endpoints for read scaling.
