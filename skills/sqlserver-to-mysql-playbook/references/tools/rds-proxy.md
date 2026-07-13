# Amazon RDS Proxy Overview

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.rdsproxy.html

**Conversion category:** N/A (tooling)
**SCT automation:** N/A — post-migration connection-management feature for the target.

## SQL Server
N/A on the source side. RDS Proxy is a target-side architectural enhancement; the playbook presents it as a benefit available after migrating to Aurora/RDS MySQL.

## MySQL
Amazon RDS Proxy is a fully managed, highly available database proxy for Amazon RDS and Aurora. Generally available for **Aurora MySQL**, Aurora PostgreSQL, Amazon RDS for MySQL, and Amazon RDS for PostgreSQL. It pools and shares database connections to improve scalability, resilience, and security for the migrated Aurora MySQL target.

## Conversion notes
- **Connection pooling:** Lets applications (incl. serverless) pool and share connections, avoiding exhaustion of database memory/compute from many or rapidly cycling connections.
- **Faster failover:** Reduces failover times for Aurora and RDS databases by up to **66%** by connecting to a new DB instance while preserving application connections.
- **Security:** Manage database credentials, authentication, and access via AWS Secrets Manager and AWS IAM.
- **No code changes:** Can be enabled for most applications with no code changes; fully compatible with supported engine protocols.
- **Fully managed:** No additional infrastructure to provision/manage or patch.
- **Highly available:** Deployed across multiple Availability Zones to protect against infrastructure failure.
- **Pricing:** Pay per vCPU of the database instance for which the proxy is enabled.
- **Benefits summary:** Improved application performance, increased availability (66% faster failover), centralized security via Secrets Manager, fully managed, fully compatible, available and durable across AZs.
