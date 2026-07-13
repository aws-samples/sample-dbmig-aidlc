# Configuring Upgrades

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.configuration.upgrades.html

**Conversion category:** N/A
**SCT automation:** N/A

## SQL Server

Database upgrades are required periodically for security fixes, bug fixes, compliance, or new features. Two approaches:

**Upgrade In-Place** — retain current hardware/OS, add new SQL Server binaries on the same server, then upgrade the instance.

Prerequisite steps:
- Back up all SQL Server database files (for restore if required).
- Run `DBCC CHECKDB` on databases to be upgraded to confirm a consistent state.
- Allocate enough disk space for SQL Server components plus user databases.
- Disable all startup stored procedures (they can block the upgrade).
- Stop all applications and services with SQL Server dependencies.

Upgrade steps:
- Install new software (fix issues raised, set automatic-update preference, select products/binaries to upgrade, monitor download/extract/install).
- Specify the SQL Server instance to upgrade; on the Select Features page, features and prerequisites are preselected.
- Review the upgrade plan before the actual upgrade.
- Monitor installation progress.

Post-upgrade tasks:
- Review the summary log file.
- Register your servers.

**Migrate to a New Installation** — build a new SQL Server environment (typically new hardware + new OS version) while keeping the current one. Migrate system objects to match, then migrate user databases via backup and restore.

## MySQL

In a managed service (Amazon RDS / Aurora MySQL), upgrades are much simpler than on-prem SQL Server.

Determine the current Aurora MySQL version via CLI:

```
aws rds describe-db-engine-versions --engine aurora-mysql --query '*[].[EngineVersion]' --output text --region your-AWS-Region
```

Or from the database:

```sql
SELECT AURORA_VERSION();
```

Version scheme example `2.08.1`: first digit is the major version. Aurora MySQL v1 ≈ MySQL 5.6; Aurora MySQL v2 ≈ MySQL 5.7.

- AWS does **not** apply major version upgrades automatically (major versions may be backward-incompatible — test applications).
- Minor upgrades can be applied automatically by configuring the RDS instance; applied during the scheduled maintenance window.

Check current automatic minor upgrade versions:

```
aws rds describe-db-engine-versions --output=table --engine mysql --engine-version minor-version --region region
```

(No results = no automatic minor upgrade scheduled.)

**In-place cluster upgrade** preserves endpoints and the set of DB instances, and is fast because data isn't copied to a new cluster volume.

Recommended simulation before production: clone the cluster → in-place upgrade the clone → test apps/performance → resolve issues → then upgrade production.

Major-upgrade pre-checks:
- Check open XA transactions with `XA RECOVER`; commit/rollback before upgrade.
- Check for in-flight DDL via `SHOW PROCESSLIST` (`CREATE`, `DROP`, `ALTER`, `RENAME`, `TRUNCATE`); let them finish.
- Check uncommitted rows via `INFORMATION_SCHEMA.INNODB_TRX`; let transactions complete or stop the apps.

Aurora performs the major upgrade in multiple monitored steps (recorded as events): pre-checks → take cluster offline + re-test → snapshot cluster volume → clone cluster volume (revert source on failure) → clean shutdown + rollback uncommitted txns → install new engine binary and upgrade data format → completion event.

**Upgrade via Console:** RDS console → Databases → select cluster → Modify → choose new DB engine version → Continue → review → optionally Apply immediately → Modify cluster.

**Upgrade via AWS CLI** (`modify-db-cluster`):

```
aws rds modify-db-cluster \
--db-cluster-identifier sample-cluster \
--engine aurora-mysql \
--engine-version 5.7.mysql_aurora.2.09.0 \
--allow-major-version-upgrade \
--apply-immediately
```

## Conversion notes

- No direct SQL-Server-to-Aurora upgrade conversion — this is an operational/process mapping, not a code conversion.
- Aurora abstracts away OS/binary management: no DBCC consistency check, disk-space sizing, startup-procedure disabling, or server registration steps.
- Major upgrades are manual/opt-in (`--allow-major-version-upgrade`); minor upgrades can be automated via the maintenance window.
- Aurora upgrades are cluster-level in-place operations preserving endpoints; back up via RDS snapshots rather than manual file backups.
- Summary mapping (SQL Server step → Aurora MySQL): instance backup → RDS instance backup; DBCC / disk sizing / disable startup procs / register server → N/A; install software & fix prereqs → commit/rollback uncommitted transactions; select instance → select correct RDS instance; monitor progress & results → reviewed from console; re-test apps and re-run in production → same.
