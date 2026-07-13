# Resource governor features

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.management.resourcegovernor.html

**Conversion category:** Manual (One star feature compatibility)
**SCT automation:** N/A

## SQL Server

SQL Server Resource Governor controls and manages resource consumption, enforcing workload limits on CPU, physical I/O, and Memory. Configurations are dynamic and changeable in real time. In SQL Server 2019, `REQUEST_MAX_MEMORY_GRANT_PERCENT` (in `CREATE/ALTER WORKLOAD GROUP`) changed from integer to float for more granular memory control.

**Use cases:** minimize performance bottlenecks/inconsistencies to support SLAs; protect against runaway queries / throttle I/O-intensive operations; track and control resource-based pricing.

**Concepts:**
* **Resource Pools** — physical resources (built-in `internal` and `default`; plus user-defined pools).
* **Workload Groups** — logical containers for similar session requests; resource limit policies are defined here; each group belongs to a pool.
* **Classification** — inspects incoming connections and assigns them to a workload group via a user-defined function.

Examples:

```sql
-- Turn on the Resource Governor
ALTER RESOURCE GOVERNOR RECONFIGURE;

-- Create a resource pool
CREATE RESOURCE POOL ReportingWorkloadPool WITH (MAX_CPU_PERCENT = 20);
ALTER RESOURCE GOVERNOR RECONFIGURE;

-- Create a workload group
CREATE WORKLOAD GROUP ReportingWorkloadGroup USING poolAdhoc;
ALTER RESOURCE GOVERNOR RECONFIGURE;

-- Create a classifier function
CREATE FUNCTION dbo.WorkloadClassifier()
RETURNS sysname WITH SCHEMABINDING
AS
BEGIN
    RETURN (CASE
        WHEN HOST_NAME() = 'ReportServer'
        THEN 'ReportingWorkloadGroup'
        ELSE 'Default'
    END)
END;

-- Register the classifier function
ALTER RESOURCE GOVERNOR WITH (CLASSIFIER_FUNCTION = dbo.WorkloadClassifier);
ALTER RESOURCE GOVERNOR RECONFIGURE;
```

## MySQL

Aurora MySQL doesn't support server-wide, granular, resource-based workload isolation like Resource Governor. It does support **User Resource Limit Options** (part of `CREATE USER`) for high-level limits per user:
* Total queries per hour.
* Updates per hour.
* Connections established per hour.
* Total concurrent connections.

Syntax:

```sql
CREATE USER <User Name> ...
WITH
MAX_QUERIES_PER_HOUR count |
MAX_UPDATES_PER_HOUR count |
MAX_CONNECTIONS_PER_HOUR count |
MAX_USER_CONNECTIONS count
```

Example:

```sql
CREATE USER 'ReportUsers'@'localhost'
IDENTIFIED BY '<REPLACE_WITH_STRONG_PASSWORD>'
WITH
MAX_QUERIES_PER_HOUR 60
MAX_UPDATES_PER_HOUR 0
MAX_CONNECTIONS_PER_HOUR 5
MAX_USER_CONNECTIONS 2;
```

### Migration Considerations

Both limit resources per workload type, but differ in scope and flexibility. Resource Governor is a dynamically configured framework based on actual runtime consumption. User Resource Limit Options are part of security objects and require application connection changes to map to limited users (modify limits by altering the user). They limit *quantities* (queries/connections), not actual resource consumption — a single runaway query can still slow the server. When limits are exceeded, Resource Governor *throttles*; Aurora MySQL *raises errors*.

## Summary

| Feature | SQL Server Resource Governor | Aurora MySQL User Resource Limit Options | Comments |
|---|---|---|---|
| Scope | Dynamic pools/workload groups via classifier function | Per user | App connection strings must use specific limited users |
| Limited resources | I/O, CPU, memory | Number of queries, number of connections | |
| Modifying limits | `ALTER RESOURCE POOL` | `ALTER USER` | App may use a dynamic connection string |
| When threshold reached | Throttles and queues runs | Raises an error | App retry logic may be needed |

## Conversion notes
- No direct equivalent: Resource Governor (I/O/CPU/memory, throttling, classifier-based) → Aurora MySQL **User Resource Limit Options** (query/connection counts per user, error on breach).
- Requires application changes: connections must use the specific resource-limited users.
- Aurora MySQL raises errors instead of throttling — add retry logic in the application.
- No SCT automation; map workloads to users manually.
