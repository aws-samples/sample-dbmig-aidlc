# Configuring Server Options

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.configuration.serveroptions.html

**Conversion category:** Manual (one-star feature compatibility)
**SCT automation:** N/A
**Key difference:** Use cluster and database parameter groups.

## SQL Server

SQL Server provides server-level settings affecting all databases and sessions, modified via the `sp_configure` system stored procedure. Server options control:
- Hardware utilization (memory management, affinity mask, priority boost, network packet size, soft NUMA).
- Runtime global values (recovery interval, remote login timeout, optimize for ad-hoc workloads, cost threshold for parallelism).
- Global feature toggles (C2 Audit, OLE procedures, CLR procedures, trigger recursion).
- Global security (server authentication mode, remote access, `xp_cmdshell` shell access, CLR access level, database chaining).
- Session defaults (user options, default language, backup compression, fill factor).

Some settings need an explicit `RECONFIGURE`; high-risk settings need `RECONFIGURE WITH OVERRIDE`. Advanced options are hidden until `show advanced options` is set to 1. Server audits are managed via `CREATE`/`ALTER SERVER AUDIT`.

Syntax:

```sql
EXECUTE sp_configure <option>, <value>;
```

Examples:

```sql
-- Limit server memory usage to 4 GB
EXECUTE sp_configure 'show advanced options', 1;
RECONFIGURE;
sp_configure 'max server memory', 4096;
RECONFIGURE;

-- Allow command shell access from T-SQL
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1;
RECONFIGURE;

-- View current values
EXECUTE sp_configure
```

## MySQL

In Aurora MySQL, "database" and "schema" are synonymous, so SQL Server database options don't apply. The Aurora equivalent of SQL Server database/server options are **Server System Variables**, modifiable via:
- MySQL command line utility.
- Aurora DB Cluster and DB Instance Parameters.
- System variables used by the SQL `SET` command.

The Aurora MySQL default parameter group lists more than 250 parameters. Unlike standalone MySQL, Aurora provides no file-system access to the config file; some parameters can't be modified and others were removed (many are viewable but not modifiable). Most settings are not compatible with SQL Server, except obvious ones like `max server memory` ≈ `innodb_buffer_pool_size`.

In most cases use the default parameter groups (optimized for common use cases). Aurora is a cluster of DB instances, so some parameters apply cluster-wide and others per-instance:

| Aurora MySQL parameter class | Controlled by |
|---|---|
| **Cluster-level parameters** (e.g., `aurora_load_from_s3_role`, `default_password_lifetime`, `default_storage_engine`) | Cluster parameter groups — one cluster parameter group per Aurora cluster. |
| **DB instance-level parameters** (e.g., `autocommit`, `connect_timeout`, `innodb_change_buffer_max_size`) | DB parameter groups — each instance in the cluster can use a unique DB parameter group. |

Syntax — server-level options set with `SET GLOBAL`:

```sql
SET GLOBAL <option> = <Value>;
```

Example — decrease compression level to reduce CPU usage:

```sql
SET GLOBAL innodb_compression_level = 5;
```

**Create a parameter group:**
1. Navigate to **Parameter group** in the RDS service of the AWS Console.
2. Choose **Create parameter group** (you can't edit the default — create a custom group).
3. For **Parameter group family**, choose `aurora-mysql5.7`.
4. For **Type**, choose **DB Parameter Group** (or **Cluster Parameter Group** for cluster parameters).
5. Choose **Create**.

**Modify a parameter group:**
1. Navigate to **Parameter group** in the RDS service of the AWS Console.
2. Choose the parameter group name.
3. Choose **Edit parameters**.
4. Change values and choose **Save changes**.

## Conversion notes

- No automatic conversion: SQL Server `sp_configure` / `RECONFIGURE` settings must be mapped manually to Aurora system variables.
- Cluster-wide vs per-instance distinction is key: choose cluster parameter groups vs DB parameter groups accordingly.
- The default parameter group cannot be edited — create a custom parameter group (family `aurora-mysql5.7`) to change values.
- Few SQL Server settings have direct equivalents; notable one is `max server memory` ≈ `innodb_buffer_pool_size`.
- Many MySQL parameters are viewable but not modifiable in Aurora; no file-system config access.
- `xp_cmdshell` / OS-shell and CLR/OLE features have no Aurora equivalent.
