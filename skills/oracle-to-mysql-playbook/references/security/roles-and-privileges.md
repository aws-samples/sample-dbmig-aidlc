# Oracle Roles and MySQL Privileges

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.security.roles.html

**Conversion category:** Assisted
**SCT automation:** N/A

Key difference: there are no roles in MySQL 5.7, only privileges. (MySQL 8 / RDS MySQL 8 reintroduces roles.)

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

In MySQL 5.7 there is no ROLE feature — you must grant the required privileges directly, though wildcards let you target multiple objects in one statement.

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

- MySQL 5.7 has no roles — flatten each Oracle role into the explicit set of privileges and `GRANT` them directly to each user. Conversion is assisted because the privilege mapping must be reviewed manually.
- Target MySQL 8 / Aurora MySQL 8 where possible: it supports `CREATE ROLE` / `GRANT role TO user`, allowing a closer mapping of Oracle roles. Note that granted roles must be activated (`SET ROLE` / `activate_all_roles_on_login`).
- Oracle 12c common (`c##`) vs. local roles are tied to the CDB/PDB model, which MySQL lacks; collapse them into ordinary MySQL roles/privileges.
- Watch privilege-scope differences: Oracle system privileges (e.g. `ALTER SYSTEM`, `SELECT ANY DICTIONARY`, `RESOURCE`) often have no one-to-one MySQL counterpart and may map to global (`*.*`), database (`db.*`), or object-level grants — or to managed-service limitations on RDS/Aurora.
- Be mindful of the MySQL 8 `SYSTEM_USER` privilege: `GRANT ALL ON *.*` includes it, which affects who can manage system accounts.
