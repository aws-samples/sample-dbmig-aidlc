# Amazon RDS Proxy overview

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tools.rdsproxy.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PG 18 support check, session-pinning caveat for converted T-SQL, Npgsql pooling note.

> **Content security review** (2026-11-18): the 66% failover figure now cites the RDS Proxy FAQs and the AWS Database Blog measurements.

## SQL Server
- Not applicable as a source consideration. RDS Proxy is a **target-side** connection-management layer; it does not proxy SQL Server.

## PostgreSQL
- RDS Proxy is generally available for **Aurora PostgreSQL** and Amazon RDS for PostgreSQL (also Aurora MySQL and RDS for MySQL).
- Sits in front of the target Aurora/RDS database to pool and share application connections, improving scalability and resilience after migration.

## Conversion notes
- **What it is:** A fully managed, highly available database proxy for Amazon RDS that makes applications more scalable, more resilient to database failures, and more secure.
- **Problem it solves:** Applications (especially serverless) can open/close many connections at a high rate, exhausting DB memory and compute. RDS Proxy pools and shares established connections.
- **Benefits:**
  - **Improved performance** — connection pooling reduces stress on DB compute/memory; efficiently supports a large number/frequency of connections.
  - **Increased availability** — reduces failover times by up to **66%** for Amazon RDS and Aurora Multi-AZ databases, because it bypasses DNS caches and keeps application connections open while it connects to the new instance ([Amazon RDS Proxy FAQs](https://aws.amazon.com/rds/proxy/faqs/); measured client recovery times: [Improving application availability with Amazon RDS Proxy](https://aws.amazon.com/blogs/database/improving-application-availability-with-amazon-rds-proxy/)).
  - **Security** — centrally manage DB credentials via AWS Secrets Manager; integrates with AWS IAM for authentication/access.
  - **Fully managed** — no proxy server to patch/manage; no additional infrastructure to provision.
  - **Fully compatible** — compatible with supported DB engine protocols; deploy with **no application code changes** for most applications.
  - **Available & durable** — deployed across multiple Availability Zones (AZs) to protect against infrastructure failure.
- **Pricing:** Pay per vCPU of the database instance for which the proxy is enabled.
- See: "Amazon RDS Proxy for Scalable Serverless Applications" and the Amazon RDS Proxy product page.
- Confirm RDS Proxy supports the target major version (PostgreSQL 18) on the RDS Proxy supported-engines page before go-live.
- Converted T-SQL that relies on **session state** (temp tables, `SET` options, `set_config` session variables replacing `SESSION_CONTEXT`, prepared statements in some drivers) **pins** connections and removes most pooling benefit. Review it before putting the application behind the proxy.
- For .NET applications, Npgsql's built-in pooling plus the reader endpoint is often enough; RDS Proxy mainly adds faster failover and IAM-based authentication.
