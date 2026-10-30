# Oracle Roles and MySQL Privileges

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.security.roles.html

**Conversion category:** Assisted
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Roles are native on Aurora MySQL 3 / 8.4 (5.7 text marked legacy); default roles must be set (activate_all_roles_on_login OFF, verified); column grants, rds_superuser_role limits, AWS_* integration roles, 8.4 SET_ANY_DEFINER.

Key difference: Aurora MySQL 3 and 8.4 support roles (MySQL 5.7 / Aurora MySQL 2 had only privileges), but granted roles are inactive until set as default roles.

## Oracle

Oracle roles are named groups of privileges granted to users. A role can contain individual system and object permissions as well as other roles, letting you grant many privileges in one operation.

Oracle 12c multi-tenant architecture supports:
- **Common** roles — created at the container database (CDB) level; exist in root and in every current and future pluggable database (PDB). Names must start with `c##` (configurable via `COMMON_USER_PREFIX` from 12.1.0.2).
- **Local** roles — created in a specific PDB; exist only there and may only contain roles/privileges that apply within that PDB.

A `CONTAINER` clause can be added to `CREATE ROLE` to choose the applicable container.

```sql
-- Create a common role (from CDB$ROOT)
CREATE ROLE c##common_role;

-- Create a local role (from a PDB, e.g. ORCLPDB)
CREATE ROLE local_role;

-- Grant privileges and roles to a role
GRANT RESOURCE, ALTER SYSTEM, SELECT ANY DICTIONARY TO local_role;

-- Revoke privileges and roles from a role
REVOKE RESOURCE, ALTER SYSTEM, SELECT ANY DICTIONARY FROM local_role;
```

Users granted the role inherit all privileges granted to that role.

## MySQL

**Aurora MySQL 3 and 8.4 support roles** (`CREATE ROLE`, `GRANT role TO user`, verified). MySQL 5.7 (Aurora MySQL 2) had none; there you had to grant privileges directly, using wildcards to target multiple objects:

```sql
-- Grant privileges using wildcards / object scopes
GRANT ALL ON test_db.* TO 'testuser';
GRANT CREATE USER ON *.* TO 'testuser';
GRANT SELECT ON db2.* TO 'testuser';
GRANT EXECUTE ON PROCEDURE mydb.myproc TO 'testuser';
```

**MySQL 8 / RDS MySQL 8** supports roles — named collections of privileges that can be created, dropped, granted to and revoked from accounts. The active roles for an account can be selected from those granted and changed during a session.

```sql
CREATE ROLE 'app_developer', 'app_read', 'app_write';
```

MySQL 8 also adds user account categories (system vs. regular) distinguished by the `SYSTEM_USER` privilege:

```sql
CREATE USER u1 IDENTIFIED BY 'password';
GRANT ALL ON *.* TO u1 WITH GRANT OPTION;
-- GRANT ALL includes SYSTEM_USER, so u1 can manipulate system or regular accounts
```

## Conversion notes

- Map each Oracle role to a MySQL role (`CREATE ROLE`, `GRANT … TO role`, `GRANT role TO user`). Conversion is assisted because the privilege mapping must be reviewed manually.
- **Granted roles are inactive by default:** `activate_all_roles_on_login` is OFF on both versions (verified). Run `SET DEFAULT ROLE ALL TO user` after granting (verified: recorded in `mysql.default_roles`), or users will see no role privileges — Oracle enables default roles automatically.
- Column-level grants (`GRANT SELECT (col) ON db.t TO …`) work (verified) and replace Oracle column privileges; Oracle VPD/row-level security has no equivalent (use views with `SQL SECURITY DEFINER` and a `CURRENT_USER()` predicate).
- The Aurora master user holds `rds_superuser_role`, not `SUPER` (verified: `SHOW GRANTS`), and cannot use `SET GLOBAL`, resource groups or `INNODB_REDO_LOG_ENABLE`; Oracle `DBA`-style grants must map to what `rds_superuser_role` allows.
- Aurora-specific roles `AWS_LOAD_S3_ACCESS`, `AWS_SELECT_S3_ACCESS`, `AWS_LAMBDA_ACCESS`, `AWS_SAGEMAKER_ACCESS`, `AWS_COMPREHEND_ACCESS`, `AWS_BEDROCK_ACCESS` exist on both versions (verified) and gate the AWS integrations.
- On 8.4, creating routines/views with another account as `DEFINER` needs `SET_ANY_DEFINER` (`SET_USER_ID` on 3.x).
- Oracle 12c common (`c##`) vs. local roles are tied to the CDB/PDB model, which MySQL lacks; collapse them into ordinary MySQL roles/privileges.
- Watch privilege-scope differences: Oracle system privileges (e.g. `ALTER SYSTEM`, `SELECT ANY DICTIONARY`, `RESOURCE`) often have no one-to-one MySQL counterpart and may map to global (`*.*`), database (`db.*`), or object-level grants — or to managed-service limitations on RDS/Aurora.
- Be mindful of the MySQL 8 `SYSTEM_USER` privilege: `GRANT ALL ON *.*` includes it, which affects who can manage system accounts.
