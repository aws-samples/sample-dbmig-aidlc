# Oracle and Aurora MySQL Upgrades

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.configuration.upgrades.html

**Conversion category:** N/A
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Current version schemes (3.x = 8.0, 8.4.x; verified AURORA_VERSION()), corrected the --engine mysql command, 3 → 8.4 upgrade path and its breaking changes (verified), blue/green deployments.

## Oracle

Oracle upgrades are either **minor** or **major**. A version like `11.2.0.4.0` breaks down as:

- `11` — major database version
- `2` — database maintenance version
- `0` — application server version
- `4` — component-specific version
- `0` — platform-specific version

Major upgrades change the major version number (gain new features); minor upgrades target bug and security fixes. Both first require installing the new Oracle software on the server, followed by extensive application testing before upgrading production. Oracle 18c introduces Zero-Downtime Database Upgrade to automate upgrades and potentially eliminate application downtime.

Compatibility level controls features/behaviors via the `COMPATIBLE` parameter:

```sql
SELECT NAME, VALUE FROM V$PARAMETER WHERE NAME = 'compatible';
```

The Oracle upgrade tools walk through ~eleven steps: upgrade operation type, database selection, prerequisite checks, upgrade options (recompilation, parallelism, time zone, statistics), management options, move database files, network configuration, recovery options, summary, progress, results. Manual upgrades expand these into many sub-steps.

## MySQL

In Amazon Aurora MySQL the upgrade process is managed and far simpler. Determine the current version:

```bash
aws rds describe-db-engine-versions --engine aurora-mysql --query '*[].[EngineVersion]' --output text --region your-AWS-Region
```

```sql
SELECT AURORA_VERSION();
```

Version schemes (verified with `SELECT AURORA_VERSION()`: `3.13.0` and `8.4.8`):
- Aurora MySQL **version 3** = MySQL 8.0 compatible, numbered `3.MM.p` (engine version string `8.0.mysql_aurora.3.13.0`). 3.10 is the current long-term-support (LTS) release.
- Aurora MySQL **8.4** = MySQL 8.4 LTS compatible, numbered `8.4.x` (engine version `8.4.mysql_aurora.8.4.8`).
- Versions 1 (5.6) and 2 (5.7) are past end of standard support; version 2 runs only under paid RDS Extended Support. See `../target-baseline-aurora-mysql.md` for support dates.

- **Minor upgrades** can be applied automatically by enabling auto minor version upgrade on the RDS instance; applied during the scheduled maintenance window. List available minor versions:

  ```bash
  aws rds describe-db-engine-versions --engine aurora-mysql --engine-version 8.0.mysql_aurora.3.13.0 \
    --query 'DBEngineVersions[0].ValidUpgradeTarget[].[EngineVersion,IsMajorVersionUpgrade]' --output table
  # (the original used --engine mysql, which lists RDS for MySQL, not Aurora)
  ```

- **Major upgrades** are never applied automatically (may not be backward-compatible). Application testing is highly recommended.

In-place upgrades preserve endpoints and the set of DB instances and are fast (no data copy to a new volume). To simulate safely: clone the cluster, perform an in-place upgrade of the clone, test applications/performance, resolve issues, then upgrade production.

Pre-major-upgrade checks recommended by AWS:

- Check open XA transactions with `XA RECOVER`; commit or roll them back.
- Check for in-flight DDL via `SHOW PROCESSLIST` (look for `CREATE`, `DROP`, `ALTER`, `RENAME`, `TRUNCATE`); let them finish.
- Check uncommitted rows via `INFORMATION_SCHEMA.INNODB_TRX`; let transactions complete or stop the submitting applications.

Aurora performs a major upgrade in multiple recorded steps (visible on the RDS Events page): pre-checks → take cluster offline and re-test → snapshot backup → clone cluster volume (revert source if issues) → clean shutdown rolling back uncommitted transactions → install new engine binary and convert system tables/data via the writer instance → final completion event.

**Upgrade via AWS Management Console:** RDS → Databases → select cluster → **Modify** → choose new **DB engine version** → **Continue** → optionally **Apply immediately** (may cause an outage) → **Modify cluster**.

**Upgrade via AWS CLI** (`modify-db-cluster`):

```bash
aws rds modify-db-cluster \
  --db-cluster-identifier sample-cluster \
  --engine aurora-mysql \
  --engine-version 8.4.mysql_aurora.8.4.8 \
  --db-cluster-parameter-group-name my-aurora-mysql84-params \
  --allow-major-version-upgrade \
  --apply-immediately
```

## Conversion notes

- No SCT/DMS action — this is an operational difference, not a schema conversion.
- Oracle: DBA-driven, install-software-first, many manual steps. Aurora MySQL: managed service, console/CLI-driven, in-place upgrades preserve endpoints.
- Always set `--allow-major-version-upgrade` for major version jumps; minor upgrades can be automated via the maintenance window.
- Map upgrade prerequisites: select the right RDS instance class, commit/rollback open transactions, take an RDS snapshot, and stop application connections before upgrading.
- Re-run the full test-and-upgrade flow in production after validating on a clone.
- **3 → 8.4** is an in-place major upgrade (3.13.0 lists `8.4.mysql_aurora.8.4.8` as a valid major target, verified); 2 → 8.4 is not direct — go through 3 first. Use an `aurora-mysql8.4` parameter group (parameters such as `expire_logs_days` and `binlog_transaction_dependency_tracking` no longer exist).
- Before 3 → 8.4, fix what 8.4 rejects (all verified on 8.4.8): foreign keys to non-unique keys, `AUTO_INCREMENT` on `FLOAT`/`DOUBLE`, `MASTER`/`SLAVE` replication SQL, and accounts that should move from `mysql_native_password` to `caching_sha2_password`.
- Prefer **Aurora blue/green deployments** for major upgrades of production clusters: the green cluster is upgraded and kept in sync by binlog replication, and switchover takes about a minute. Binary logging must be on.
- For a migration project, target 8.4 from the start so there is no near-term major upgrade.
