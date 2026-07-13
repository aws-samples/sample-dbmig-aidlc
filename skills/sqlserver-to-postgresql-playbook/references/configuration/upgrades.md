# Configuring Upgrades

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.configuration.upgrades.html

**Conversion category:** N/A
**SCT automation:** N/A

## SQL Server

Database upgrades are performed for security fixes, bug fixes, compliance, or new features. Two approaches: upgrade in-place or migrate to a new installation.

**Upgrade in-place** — retain current hardware/OS, add new SQL Server binaries on the same server, then upgrade the instance. Review release notes for limitations and known issues first.

Prerequisite steps:
- Back up all SQL Server database files (for restore if required).
- Run `DBCC CHECKDB` on databases to be upgraded to ensure consistent state.
- Allocate enough disk space for SQL Server components plus user databases.
- Disable all startup stored procedures (they may block the upgrade).
- Stop all applications and services with SQL Server dependencies.

Steps for upgrade:
- Install new software (fix issues raised, choose update preferences, select products/binaries to upgrade, monitor download/extract/install).
- Specify the instance of SQL Server to upgrade; on Select Features page features are preselected and prerequisites installed.
- Review the upgrade plan before the actual upgrade.
- Monitor installation progress.

Post-upgrade tasks:
- Review the summary log file.
- Register your servers.

**Migrate to a new installation** — build a new SQL Server environment (typically new hardware + new OS version) while maintaining the current one. Migrate system objects to match the existing environment, then migrate user databases via backup and restore.

## PostgreSQL

In a managed service like Amazon RDS, the upgrade process is much easier than on-premises.

Determine the current Aurora PostgreSQL version:

```bash
aws rds describe-db-engine-versions --engine aurora-postgresql --query '*[].[EngineVersion]' --output text --region your-AWS-Region
```

Or query from the database:

```sql
SELECT AURORA_VERSION();
-- aurora_version
-- 4.0.0

SHOW SERVER_VERSION;
-- server_version
-- 12.4
```

AWS does **not** apply major version upgrades automatically — they may include non-backward-compatible system table/code changes, so application testing is highly recommended. Minor upgrades can be applied automatically by configuring the RDS instance; when enabled, the upgrade occurs during the scheduled maintenance window.

Determine current automatic minor upgrade versions (Linux):

```bash
aws rds describe-db-engine-versions --engine aurora-postgresql | grep -A 1 AutoUpgrade | grep -A 2 true | grep PostgreSQL | sort --unique | sed -e 's/"Description": "//g'
```

If no results return, no automatic minor version upgrade is available/scheduled.

Recommended major upgrade process:
- Have a version-compatible parameter group ready. If using a custom DB instance/cluster parameter group, either (1) specify the default parameter group for the new engine version, or (2) create your own custom parameter group for the new version. If you associate a new parameter group as part of the upgrade, reboot the database after upgrade to apply parameters (status shows `pending-reboot`; check via `describe-db-instances` or `describe-db-clusters`).
- Check for unsupported usage:
  - Commit or roll back all open prepared transactions:
    ```sql
    SELECT count(*) FROM pg_catalog.pg_prepared_xacts;
    ```
  - Remove all uses of `reg*` data types before upgrade (except `regtype` and `regclass`, the `reg*` types cannot be upgraded — `pg_upgrade` cannot persist them):
    ```sql
    SELECT count(*) FROM pg_catalog.pg_class c, pg_catalog.pg_namespace n, pg_catalog.pg_attribute a
    WHERE c.oid = a.attrelid
      AND NOT a.attisdropped
      AND a.atttypid IN ('pg_catalog.regproc'::pg_catalog.regtype,
        'pg_catalog.regprocedure'::pg_catalog.regtype,
        'pg_catalog.regoper'::pg_catalog.regtype,
        'pg_catalog.regoperator'::pg_catalog.regtype,
        'pg_catalog.regconfig'::pg_catalog.regtype,
        'pg_catalog.regdictionary'::pg_catalog.regtype)
      AND c.relnamespace = n.oid
      AND n.nspname NOT IN ('pg_catalog', 'information_schema');
    ```
- Perform a backup (the upgrade process creates a DB cluster snapshot during upgrading).
- Upgrade certain extensions to the latest version before the major upgrade — including `pgRouting` and `postGIS`:
  ```sql
  ALTER EXTENSION PostgreSQL-extension UPDATE TO 'new-version'
  ```

Perform the upgrade via console (RDS → Databases → select cluster → Modify → choose new **DB engine version** → Continue → optionally **Apply immediately** → Modify Cluster) or AWS CLI:

```bash
# Linux, macOS, Unix
aws rds modify-db-cluster \
  --db-cluster-identifier mydbcluster \
  --engine-version new_version \
  --allow-major-version-upgrade \
  --no-apply-immediately
```

```bat
REM Windows
aws rds modify-db-cluster ^
  --db-cluster-identifier mydbcluster ^
  --engine-version new_version ^
  --allow-major-version-upgrade ^
  --no-apply-immediately
```

## Conversion notes
- Many SQL Server prerequisite/post-upgrade steps have no Aurora equivalent (N/A): DBCC consistency checks, disk-size validation, disabling startup procedures, stopping applications, reviewing pre-upgrade summary, registering servers — these are handled by the managed service.
- Aurora-specific prerequisites map to: remove `reg*` data types, upgrade extensions (pgRouting, postGIS), and commit/roll back open prepared transactions.
- Both platforms require backup beforehand and application testing afterward, plus re-running all steps in production.
- Major version upgrades require `--allow-major-version-upgrade` and a version-compatible parameter group; reboot after upgrade to apply a newly associated parameter group.
- Choosing **Apply immediately** can cause an outage; otherwise changes apply in the maintenance window.
