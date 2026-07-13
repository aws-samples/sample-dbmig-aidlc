# Configuration — Reference Index

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> Chapter: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.configuration.html

Reference content for configuring software and resource settings when migrating from Microsoft SQL Server 2019 to Amazon Aurora MySQL — database upgrades, session options, database options, and server options. Highlights Aurora MySQL's distinct approaches such as parameter groups and cluster-level settings.

| File | Topic | Conversion category | Key difference |
|---|---|---|---|
| [upgrades.md](upgrades.md) | Configuring upgrades | N/A | Aurora performs managed cluster-level in-place upgrades; major versions are opt-in, minor can be automated via maintenance window. |
| [session-options.md](session-options.md) | Configuring session options | Assisted (★★) | `SET` options differ significantly except transaction isolation; Aurora uses server system variables / `SET SESSION`. |
| [database-options.md](database-options.md) | Configuring database options | N/A (no compatibility) | SQL Server database options are inapplicable — a "database" in Aurora MySQL is a schema. |
| [server-options.md](server-options.md) | Configuring server options | Manual (★) | `sp_configure`/`RECONFIGURE` → Aurora cluster and DB parameter groups; few direct equivalents. |

## Cross-cutting themes

- Aurora MySQL manages runtime configuration through **DB cluster parameter groups** (cluster-wide) and **DB parameter groups** (per-instance), not config files or `sp_configure`.
- The default parameter group is read-only; create a custom group (family `aurora-mysql5.7`) to change values.
- "Database" and "schema" are synonymous in Aurora MySQL, so SQL Server database-level options have no equivalent.
- Most SQL Server settings have no Aurora counterpart; a notable exception is `max server memory` ≈ `innodb_buffer_pool_size`.
