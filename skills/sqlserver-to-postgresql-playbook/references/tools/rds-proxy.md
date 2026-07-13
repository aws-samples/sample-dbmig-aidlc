# Amazon RDS Proxy overview

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tools.rdsproxy.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A

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
  - **Increased availability** — reduces fail-over time by up to **66%** by connecting to a new DB instance while preserving application connections.
  - **Security** — centrally manage DB credentials via AWS Secrets Manager; integrates with AWS IAM for authentication/access.
  - **Fully managed** — no proxy server to patch/manage; no additional infrastructure to provision.
  - **Fully compatible** — compatible with supported DB engine protocols; deploy with **no application code changes** for most applications.
  - **Available & durable** — deployed across multiple Availability Zones (AZs) to protect against infrastructure failure.
- **Pricing:** Pay per vCPU of the database instance for which the proxy is enabled.
- See: "Amazon RDS Proxy for Scalable Serverless Applications" and the Amazon RDS Proxy product page.
