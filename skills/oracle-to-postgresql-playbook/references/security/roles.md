# Oracle and PostgreSQL Roles

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.security.roles.html

**Conversion category:** Assisted (Three star feature compatibility — syntax/option differences, similar functionality)
**SCT automation:** N/A

Key difference: There are no users, only roles, in PostgreSQL.

## Oracle

Oracle roles are groups of privileges granted to users. A role can contain individual system and object permissions as well as other roles, letting you grant multiple privileges in one operation.

Oracle 12c multi-tenant architecture supports two role scopes:
- **Common roles** — created at the container database (CDB) level; exist in the root and in every existing and future pluggable database (PDB). Useful for cross-container operations. Common role names must start with the `c##` prefix (changeable via `COMMON_USER_PREFIX` starting in 12.1.0.2).
- **Local roles** — created in a specific PDB; exist only in that PDB and can contain only roles/privileges that apply within it.

A `CONTAINER` clause can be added to `CREATE ROLE` to choose the applicable container.

**Examples**

Create a common role (from root):

```sql
show con_name

CON_NAME
CDB$ROOT

CREATE ROLE c##common_role;

Role created.
```

Create a local role (from a PDB):

```sql
show con_name

CON_NAME
ORCLPDB

CREATE ROLE local_role;

Role created.
```

Grant and revoke privileges/roles to/from a role:

```sql
GRANT RESOURCE, ALTER SYSTEM, SELECT ANY DICTIONARY TO local_role;

REVOKE RESOURCE, ALTER SYSTEM, SELECT ANY DICTIONARY FROM local_role;
```

Users granted `local_role` then have all privileges granted to that role.

## PostgreSQL

In PostgreSQL, roles **without login permission** are similar to Oracle database roles. PostgreSQL roles are most like Oracle 12c **common roles** — they are defined at the database **cluster** level and are global/valid across all databases in the cluster.

- A role is a database entity that can own objects and have database privileges.
- A role can be a user, a group, or both, depending on how it is used.
- Roles with **connect/LOGIN** permission are essentially database users.
- Schemas are created **separately** from roles/users in PostgreSQL.
- `CREATE USER` is an alias for `CREATE ROLE` with one difference: `CREATE USER` automatically adds `LOGIN` so the role can access the database as a user. For Oracle-role-like (non-login) roles, use `CREATE ROLE`.

When you provision a new Aurora cluster, a root user is created as the most powerful user.

**Oracle → PostgreSQL mapping**

| Oracle | PostgreSQL |
|---|---|
| Common database user (12c) | Database role with Login |
| Local database user (12c) | N/A |
| Database user (11g) | Database role with Login |
| Database role | Database role without Login |
| Database users are identical to schema | Database users and schemas are created separately |

**Examples**

Create a non-login role and grant DML on a table:

```sql
CREATE ROLE hr_role;
GRANT SELECT, INSERT, DELETE on hr.employees to hr_role;
```

Create login roles (with password):

```sql
CREATE USER test_user1 WITH PASSWORD 'password';

CREATE ROLE test_user2 WITH LOGIN PASSWORD 'password';
```

Create a login role with a password expiration date:

```sql
CREATE ROLE test_user3 WITH LOGIN PASSWORD 'password' VALID UNTIL '2018-01-01';
```

Create a powerful non-login role that can create databases, and assign it to a user:

```sql
CREATE ROLE db_admin WITH CREATEDB;

GRANT db_admin TO test_user1;
```

Create a schema and a table inside it:

```sql
CREATE SCHEMA hello_world;

CREATE TABLE hello_world.test_table1 (a int);
```

## Conversion notes

Side-by-side equivalents (Oracle → PostgreSQL):

| Description | Oracle | PostgreSQL |
|---|---|---|
| List all roles | `SELECT * FROM dba_roles;` | `SELECT * FROM pg_roles;` |
| Create a new role | `CREATE ROLE c##common_role;` or `CREATE ROLE local_role1;` | `CREATE ROLE test_role;` |
| Grant one role to another role | `GRANT local_role1 TO local_role2;` | `grant myrole1 to myrole2;` |
| Grant privileges on a DB object to a role | `GRANT CREATE TABLE TO local_role;` | `GRANT create ON DATABASE postgresdb to test_user;` |
| Grant DML on an object to a role | `GRANT ... hr.employees to myrole1;` | `GRANT INSERT, DELETE ON hr.employees to myrole1;` |
| List all database users | `SELECT * FROM dba_users;` | `SELECT * FROM pg_user;` |
| Create a database user | `CREATE USER c##test_user IDENTIFIED BY test_user;` | `CREATE ROLE test_user WITH LOGIN PASSWORD 'test_user';` |
| Change a user's password | `ALTER USER c##test_user IDENTIFIED BY test_user;` | `ALTER ROLE test_user WITH LOGIN PASSWORD 'test_user';` |
| External authentication | Supported via Externally Identified Users | Not currently supported; future IAM-user support possible |
| Tablespace quotas | `ALTER User c##test_user QUOTA UNLIMITED ON TABLESPACE users;` | Not supported |
| Grant role to user | `GRANT my_role TO c##test_user;` | `GRANT my_role TO test_user;` |
| Lock user | `ALTER USER c##test_user ACCOUNT LOCK;` | `ALTER ROLE test_user WITH NOLOGIN;` |
| Unlock user | `ALTER USER c##test_user ACCOUNT UNLOCK;` | `ALTER ROLE test_user WITH LOGIN;` |
| Grant privileges | `GRANT CREATE TABLE TO c##test_user;` | `GRANT create ON DATABASE postgres to test_user;` |
| Default tablespace | `ALTER USER C##test_user default tablespace users;` | `ALTER ROLE test_user SET default_tablespace = 'pg_global';` |
| Grant SELECT on a table | `GRANT SELECT ON hr.employees to c##test_user;` | `GRANT SELECT ON hr.employees to test_user;` |
| Grant DML on a table | `GRANT INSERT,DELETE ON hr.employees to c##test_user;` | `GRANT INSERT,DELETE ON hr.employees to test_user;` |
| Grant execute | `GRANT EXECUTE ON hr.procedure_name to c##test_user;` | `grant execute on function "newdate"() to test_user;` (specify argument types in brackets) |
| Limit user connections | `CREATE PROFILE app_users LIMIT SESSIONS_PER_USER 5; ALTER USER C##TEST_USER PROFILE app_users;` | `ALTER ROLE test_user WITH CONNECTION LIMIT 5;` |
| Create a new schema | `CREATE USER my_app_schema IDENTIFIED BY password;` | `CREATE SCHEMA my_app_schema;` |

Gotchas and Aurora-specific notes:
- **No user/role distinction in PostgreSQL** — a "user" is just a role with `LOGIN`. Convert Oracle roles to `CREATE ROLE` (no login) and Oracle users to roles `WITH LOGIN`.
- **Local roles have no equivalent** — Oracle 12c local (per-PDB) roles map to N/A; PostgreSQL roles are always cluster-global, like Oracle common roles.
- **Schemas are decoupled from users** — in Oracle a user equals a schema; in PostgreSQL you must create schemas separately (`CREATE SCHEMA`).
- **No tablespace quotas** in PostgreSQL.
- **External authentication** (e.g., Kerberos/externally identified users) is not currently supported; potential future IAM-user support.
- Account lock/unlock is emulated with `NOLOGIN`/`LOGIN`; connection limits use `CONNECTION LIMIT` instead of Oracle profiles.
- Reference: PostgreSQL `CREATE ROLE` documentation.
