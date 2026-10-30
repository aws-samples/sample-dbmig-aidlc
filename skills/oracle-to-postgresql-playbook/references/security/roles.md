# Oracle and PostgreSQL Roles

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.security.roles.html

**Conversion category:** Assisted (Three star feature compatibility — syntax/option differences, similar functionality)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): master user is `rds_superuser` (not superuser), predefined roles (PG 14–18), PG 16 grant options, PG 15 public-schema change, IAM/Kerberos auth now supported, fixed the `pg_global` mapping, masking/RLS mappings.

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

When you provision a new Aurora cluster, a master user is created. It is **not** a PostgreSQL superuser. It is a member of `rds_superuser` (verified on 18.6), which can create roles, databases and most extensions, but cannot read `pg_authid`, use server files, or bypass some superuser-only checks.

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
CREATE ROLE test_user3 WITH LOGIN PASSWORD 'password' VALID UNTIL '2030-01-01';
```

> Never put real passwords in migration scripts. Passwords are stored as SCRAM-SHA-256 by default (`password_encryption = scram-sha-256`); MD5 passwords are deprecated in PostgreSQL 18 and trigger warnings (`md5_password_warnings`).

**Predefined roles** (PostgreSQL 14–18, present on Aurora 18.6) replace many Oracle system privileges:

| Oracle | PostgreSQL predefined role |
|---|---|
| `SELECT ANY TABLE` | `pg_read_all_data` (PG 14) |
| `INSERT/UPDATE/DELETE ANY TABLE` | `pg_write_all_data` (PG 14) |
| `ANALYZE ANY` / maintenance of other users' tables | `pg_maintain` (PG 17): `VACUUM`, `ANALYZE`, `REINDEX`, `REFRESH MATERIALIZED VIEW`, `CLUSTER`, `LOCK TABLE`; also grantable per table with `GRANT MAINTAIN ON t` |
| `SELECT_CATALOG_ROLE` / `SELECT ANY DICTIONARY` | `pg_read_all_settings`, `pg_read_all_stats`, `pg_monitor` |
| `ALTER SYSTEM KILL SESSION` | `pg_signal_backend` (and `pg_signal_autovacuum_worker`, PG 18) |
| — | `pg_create_subscription` (PG 16), `pg_checkpoint` (PG 15), `pg_use_reserved_connections` (PG 16) |

**Role membership options (PG 16+)**: `GRANT r TO u WITH INHERIT FALSE, SET TRUE` grants a role the user can switch to with `SET ROLE` but does not inherit automatically, similar to an Oracle non-default role enabled with `SET ROLE`. `WITH ADMIN OPTION` corresponds to Oracle's `WITH ADMIN OPTION`.

**Public schema (PG 15+)**: `PUBLIC` no longer has `CREATE` on schema `public` (verified on 18.6). Create an application schema per former Oracle user and grant explicitly.

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
| External authentication | Supported via Externally Identified Users | **IAM database authentication** (`GRANT rds_iam TO u`, token instead of password) or **Kerberos** through AWS Directory Service / self-managed AD (`GRANT rds_ad TO u`). The `pg_ad_mapping` extension (preload required) maps AD groups to roles. |
| Tablespace quotas | `ALTER User c##test_user QUOTA UNLIMITED ON TABLESPACE users;` | Not supported (Aurora storage is a single shared volume) |
| Grant role to user | `GRANT my_role TO c##test_user;` | `GRANT my_role TO test_user;` |
| Lock user | `ALTER USER c##test_user ACCOUNT LOCK;` | `ALTER ROLE test_user WITH NOLOGIN;` |
| Unlock user | `ALTER USER c##test_user ACCOUNT UNLOCK;` | `ALTER ROLE test_user WITH LOGIN;` |
| Grant privileges | `GRANT CREATE TABLE TO c##test_user;` | `GRANT create ON DATABASE postgres to test_user;` |
| Default tablespace | `ALTER USER C##test_user default tablespace users;` | Usually omit. On Aurora, tablespaces are logical only (all data is on the cluster volume). `pg_global` holds shared catalogs only, and user tables there fail (`permission denied for tablespace pg_global`, verified). |
| Grant SELECT on a table | `GRANT SELECT ON hr.employees to c##test_user;` | `GRANT SELECT ON hr.employees to test_user;` |
| Grant DML on a table | `GRANT INSERT,DELETE ON hr.employees to c##test_user;` | `GRANT INSERT,DELETE ON hr.employees to test_user;` |
| Grant execute | `GRANT EXECUTE ON hr.procedure_name to c##test_user;` | `grant execute on function "newdate"() to test_user;` (specify argument types in brackets) |
| Limit user connections | `CREATE PROFILE app_users LIMIT SESSIONS_PER_USER 5; ALTER USER C##TEST_USER PROFILE app_users;` | `ALTER ROLE test_user WITH CONNECTION LIMIT 5;` |
| Profile `IDLE_TIME` / `CONNECT_TIME` | `CREATE PROFILE … LIMIT IDLE_TIME 30` | `ALTER ROLE u SET idle_session_timeout = '30min';` / `ALTER ROLE u SET transaction_timeout = '…'` (PG 17) |
| Data Redaction (`DBMS_REDACT`) | Redaction policies | Aurora `pg_columnmask` extension (1.1.0 on 18.6: `pgcolumnmask.create_masking_policy`, `mask_text`, `mask_email`), or views + column privileges |
| Virtual Private Database (`DBMS_RLS`) | VPD policies | Row-level security: `ALTER TABLE t ENABLE ROW LEVEL SECURITY; CREATE POLICY …` (verified) |
| Create a new schema | `CREATE USER my_app_schema IDENTIFIED BY password;` | `CREATE SCHEMA my_app_schema;` |

Gotchas and Aurora-specific notes:
- **No user/role distinction in PostgreSQL** — a "user" is just a role with `LOGIN`. Convert Oracle roles to `CREATE ROLE` (no login) and Oracle users to roles `WITH LOGIN`.
- **Local roles have no equivalent** — Oracle 12c local (per-PDB) roles map to N/A; PostgreSQL roles are always cluster-global, like Oracle common roles.
- **Schemas are decoupled from users** — in Oracle a user equals a schema; in PostgreSQL you must create schemas separately (`CREATE SCHEMA`).
- **No tablespace quotas** in PostgreSQL.
- **External authentication**: use IAM database authentication or Kerberos (AWS Managed Microsoft AD). Both are supported on Aurora PostgreSQL. Password policy (complexity, lockout after failed logins) has no in-database equivalent; enforce it in the identity provider.
- `CREATEROLE` (PG 16+) no longer lets a role manage roles it did not create, unless it was granted `ADMIN OPTION` on them. Grant admin explicitly to delegated "user admin" roles.
- Audit: Oracle unified/standard auditing → `pgaudit` (available on Aurora 18; preload required) + CloudWatch Logs export, or Database Activity Streams.
- Account lock/unlock is emulated with `NOLOGIN`/`LOGIN`; connection limits use `CONNECTION LIMIT` instead of Oracle profiles.
- Reference: PostgreSQL `CREATE ROLE` documentation.
