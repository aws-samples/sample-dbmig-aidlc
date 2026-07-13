# Oracle and Aurora for PostgreSQL Upgrades

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.configuration.upgrades.html

**Conversion category:** N/A (config/operations topic)
**SCT automation:** N/A

## Oracle

Database upgrades are periodically required for security fixes, bug fixes, or new features. Oracle divides upgrades into **minor** and **major** types. The first step for either type is to install the new Oracle software on the server, followed by extensive application testing before upgrading a production database. Oracle 18c introduced **Zero-Downtime Database Upgrade** to automate the process and potentially eliminate application downtime.

**Version numbering** — Oracle versions are 4 (sometimes 5) numbers separated by dots. Example `11.2.0.4.0`:
* `11` — major database version
* `2` — database maintenance version
* `0` — application server version
* `4` — component specific version
* `0` — platform specific version

**Major vs minor:** A major upgrade changes the first number (`11`) and is done to gain new features. A minor upgrade changes any subsequent number (`2.0.4.0`) and focuses on bug and security fixes. The process is the same overall; minor has fewer steps.

**Compatibility level** — set with the `COMPATIBLE` parameter to control features/behaviors. Query its value:

```sql
SELECT NAME, VALUE FROM V$PARAMETER WHERE NAME = 'compatible';
```

**Upgrade process (Oracle tools):** Oracle's upgrade tools step through: Upgrade operation type → Database selection → Prerequisite checks → Upgrade options (recompilation, parallelism, time zone upgrade, statistics gathering) → Management options → Move database files → Network configuration (listener) → Recovery options → Summary → Progress → Results. A manual process splits these into many sub-steps and commands.

## PostgreSQL

On Amazon RDS / Aurora PostgreSQL, the managed-service upgrade process is much simpler than on-prem Oracle.

**Determine current version** via AWS CLI:

```bash
aws rds describe-db-engine-versions
  --engine aurora-postgresql
  --query '*[].[EngineVersion]'
  --output text
  --region your-AWS-Region
```

Or from the database:

```sql
SELECT AURORA_VERSION();
-- aurora_version
-- 4.0.0

SHOW SERVER_VERSION;
-- server_version
-- 12.4
```

**Minor upgrades** can be automatic — enable on the RDS instance and they apply during the scheduled maintenance window. To find current automatic minor upgrade versions (Linux):

```bash
aws rds describe-db-engine-versions
  --engine aurora-postgresql
  | grep -A 1 AutoUpgrade
  | grep -A 2 true
  | grep PostgreSQL
  | sort --unique
  | sed -e 's/"Description":"//g'
```

No results = no automatic minor upgrade scheduled.

**Major upgrades** are never applied automatically by AWS (system table / code changes may not be backward-compatible; application testing strongly recommended). Recommended process:

1. **Have a version-compatible parameter group ready.** If using a custom DB instance/cluster parameter group, either specify the default for the new engine version, or create your own custom group. If associating a new parameter group during upgrade, **reboot after upgrade** to apply parameters (status shows `pending-reboot`; check via `describe-db-instances` / `describe-db-clusters`).
2. **Check for unsupported usage:**
   * Commit or roll back all open prepared transactions first:
     ```sql
     SELECT count(*) FROM pg_catalog.pg_prepared_xacts;
     ```
   * Remove all uses of `reg*` data types (except `regtype` and `regclass`, which can be persisted). `pg_upgrade` can't persist these. Verify per database:
     ```sql
     SELECT count(*)
       FROM pg_catalog.pg_class c,
       pg_catalog.pg_namespace n,
       pg_catalog.pg_attribute a
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
3. **Perform a backup.** The upgrade creates a DB cluster snapshot automatically; an additional manual backup is optional.
4. **Upgrade `pgRouting` and `postGIS` extensions** to the latest available version before the major upgrade:
   ```sql
   ALTER EXTENSION PostgreSQL-extension UPDATE TO 'new-version'
   ```

Upgrades from versions older than 12 require additional steps.

**Perform the upgrade — AWS Console:** RDS → Databases → select cluster → Modify → choose new **DB engine version** → Continue → review summary → optionally **Apply immediately** (can cause an outage) → Modify cluster.

**Perform the upgrade — AWS CLI** (Linux/macOS/Unix):

```bash
aws rds modify-db-cluster \
  --db-cluster-identifier mydbcluster \
  --engine-version new_version \
  --allow-major-version-upgrade \
  --no-apply-immediately
```

Windows (`^` line continuation):

```bat
aws rds modify-db-cluster ^
  --db-cluster-identifier mydbcluster ^
  --engine-version new_version ^
  --allow-major-version-upgrade ^
  --no-apply-immediately
```

## Conversion notes

- Oracle requires installing new binaries and running multi-step upgrade tooling; Aurora upgrades are managed — pick a version and modify the cluster.
- Oracle→Aurora upgrade-step mapping (Summary table):
  - Install new Oracle software → N/A on Aurora
  - Database selection → select the right Amazon RDS instance
  - Prerequisite checks → remove `reg*` data types, upgrade extensions, commit/roll back open prepared transactions (`SELECT count(*) FROM pg_catalog.pg_prepared_xacts;`)
  - Perform a database backup → run Amazon RDS instance backup (snapshot is auto-created)
  - Stop application and connection → same
  - Progress / Results → review status from the console
  - Test applications / re-run in production → same
- Major version upgrades are **never automatic** on Aurora; minor upgrades **can** be enabled to run during the maintenance window.
- Reboot after associating a new parameter group during an upgrade or parameters won't apply (`pending-reboot` status).
- Always test against a non-production environment first.
