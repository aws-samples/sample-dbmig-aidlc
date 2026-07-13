# Users and Roles

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.security.usersroles.html

**Conversion category:** Assisted (three-star compatibility — syntax and option differences, similar functionality; there are no users in PostgreSQL, only roles)
**SCT automation:** N/A

## SQL Server

SQL Server has two layers of security principals: **logins** at the server level and **users** at the database level. Logins map to users in one or more databases. Server-level permissions (e.g., database creator, system administrator, security administrator) are not mapped to particular databases.

SQL Server supports roles at both the server and database levels. At the database level there are built-in roles (`db_owner`, `db_datareader`, `db_securityadmin`, etc.) and custom roles. A user can belong to multiple roles (all users belong to `public` by default and cannot be removed). Grant permissions to roles, then assign users to roles to simplify management.

Logins authenticate via **Windows Authentication** (Active Directory single sign-on) or **SQL authentication** (password, certificate, or asymmetric key). For backward compatibility, each database has built-in schemas including `dbo` (owned by `db_owner`); sysadmin logins map to `dbo` in each database — these typically don't need migrating.

Examples:

```sql
-- Create a login
CREATE LOGIN MyLogin WITH PASSWORD = '<REPLACE_WITH_STRONG_PASSWORD>'

-- Create a database user for the login
USE MyDatabase; CREATE USER MyUser FOR LOGIN MyLogin;

-- Assign a login to a server role
ALTER SERVER ROLE dbcreator ADD MEMBER 'MyLogin'

-- Assign a user to a database role
ALTER ROLE db_datareader ADD MEMBER 'MyUser';
```

## PostgreSQL

PostgreSQL supports only **roles** — there are no users. `CREATE USER` exists but is an alias for `CREATE ROLE` that automatically includes the `LOGIN` permission. Roles are defined at the database cluster level and are valid across all databases in the cluster.

Syntax (simplified `CREATE ROLE`):

```sql
CREATE ROLE name [ [ WITH ] option [ ... ] ]

where option can be:
  SUPERUSER | NOSUPERUSER
  | CREATEDB | NOCREATEDB
  | CREATEROLE | NOCREATEROLE
  | INHERIT | NOINHERIT
  | LOGIN | NOLOGIN
  | REPLICATION | NOREPLICATION
  | BYPASSRLS | NOBYPASSRLS
  | CONNECTION LIMIT connlimit
  | [ ENCRYPTED | UNENCRYPTED ] PASSWORD 'password'
  | VALID UNTIL 'timestamp'
  | IN ROLE role_name [, ...]
  | IN GROUP role_name [, ...]
  | ROLE role_name [, ...]
  | ADMIN role_name [, ...]
  | USER role_name [, ...]
  | SYSID uid
```

The `UNENCRYPTED PASSWORD` option was dropped in PostgreSQL 10 — passwords must be kept encrypted.

Example — create a role that can create databases (but not log in), and grant table privileges:

```sql
CREATE ROLE hr_role;
GRANT SELECT, INSERT, DELETE on hr.employees to hr_role;
```

## Conversion notes

- **No login/user distinction in PostgreSQL.** SQL Server's two-tier model (server login + database user) collapses into a single cluster-wide role. A role with `LOGIN` is the equivalent of a SQL Server login; `CREATE USER` = `CREATE ROLE ... LOGIN`.
- Roles are cluster-wide and valid in all databases, unlike SQL Server users which are scoped per database.
- **No Windows Authentication equivalent** (listed as N/A). Re-model external authentication (e.g., use IAM database authentication or password auth).
- Passwords must be encrypted (PostgreSQL 10+ dropped `UNENCRYPTED PASSWORD`).
- The `dbo` schema and other built-in SQL Server schemas typically don't need to be migrated.
- Use role membership and `GRANT`/`REVOKE` to replace SQL Server built-in roles; there is no direct mapping for `db_owner`, `db_datareader`, etc.

### Task comparison

| Task | SQL Server | Aurora PostgreSQL |
|---|---|---|
| View database users | `SELECT Name FROM sys.sysusers` | `SELECT * FROM pg_roles where rolcanlogin = true;` |
| Create a user and password | `CREATE USER <User Name> WITH PASSWORD = <PassWord>;` | `CREATE USER <User Name> WITH PASSWORD '<PassWord>';` |
| Create a role | `CREATE ROLE <Role Name>` | `CREATE ROLE <Role Name>` |
| Change a user's password | `ALTER LOGIN <SQL Login> WITH PASSWORD = <PassWord>;` | `ALTER USER <SQL Login> WITH PASSWORD '<PassWord>';` |
| External authentication | Windows Authentication | N/A |
| Add a user to a role | `ALTER ROLE <Role Name> ADD MEMBER <User Name>` | `ALTER ROLE <Role Name> SET <property and value>` |
| Lock a user | `ALTER LOGIN <Login Name> DISABLE` | `REVOKE CONNECT ON DATABASE <database_name> from <Role Name>;` |
| Grant `SELECT` on a schema | `GRANT SELECT ON SCHEMA::<Schema Name> to <User Name>` | `GRANT SELECT ON ALL TABLES IN SCHEMA <Schema Name> TO <User Name>;` |
