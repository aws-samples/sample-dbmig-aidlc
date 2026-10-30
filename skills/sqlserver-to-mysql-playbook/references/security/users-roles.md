# Users and Roles

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.security.usersroles.html

**Conversion category:** Manual
**SCT automation:** N/A (two-star feature compatibility; no native role support — use AWS IAM accounts with the AWS Authentication Plugin)

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Roles are native on 3 / 8.4 (corrected, verified); default roles must be set; fixed-role mappings, rds_superuser_role, auth plugin defaults per version, password policy options (verified), corrected the IAM AS 'RDS' example.

## SQL Server

SQL Server has two layers of security principals: **Logins** at the server level and **Users** at the database level. Logins map to users in one or more databases. Server-level permissions not mapped to databases include Database Creator, System Administrator, and Security Administrator.

SQL Server supports **Roles** at both server and database levels. At the database level, administrators can create custom roles in addition to built-in roles (`db_owner`, `db_datareader`, `db_securityadmin`, etc.). A user can belong to multiple roles (all users belong to `public` by default and can't be removed). Granting permissions to roles, then assigning users to roles, simplifies security management.

Logins authenticate via **Windows Authentication** (Active Directory single sign-on, supports individual users and domain groups) or **SQL Authentication** (managed by SQL Server, requires password/certificate/asymmetric key).

For backward compatibility each database has several schemas including `dbo` (owned by `db_owner`). Logins with sysadmin privileges map automatically to `dbo` in each database; these schemas typically don't need to be migrated.

Examples:

```sql
-- Create a login
CREATE LOGIN MyLogin WITH PASSWORD = '<REPLACE_WITH_STRONG_PASSWORD>'

-- Create a database user for MyLogin
USE MyDatabase; CREATE USER MyUser FOR LOGIN MyLogin;

-- Assign MyLogin to a server role
ALTER SERVER ROLE dbcreator ADD MEMBER 'MyLogin'

-- Assign MyUser to the db_datareader role
ALTER ROLE db_datareader ADD MEMBER 'MyUser';
```

## MySQL

*(corrected)* **Aurora MySQL 3 and 8.4 support roles** (`CREATE ROLE`, `GRANT … TO role`, `GRANT role TO user`, verified). Only Aurora MySQL 2 (5.7) lacked them. Administrators specify privileges for individual users. Aurora MySQL uses database user accounts to authenticate sessions and authorize access to objects. Wildcards can specify multiple privileges for multiple objects.

> In Aurora MySQL, a database is equivalent to a SQL Server schema.

With **IAM database authentication**, roles are available as part of the IAM framework. Authentication uses tokens instead of passwords — AWS Signature Version 4 generates tokens with a 15-minute lifetime, so user credentials need not be stored in the database. IAM can be used alongside standard database authentication. The **AWS Authentication Plugin** lets IAM-account users authenticate with access tokens, similar to SQL Server Windows Authentication.

IAM database authentication benefits:
- Supports roles for simplifying user/access management.
- Single sign-on, safer than MySQL-managed passwords.
- Encrypts network traffic with SSL.
- Centrally managed access to database resources.

> IAM database authentication limits new connections to 20 connections/second.

Aurora MySQL 3 and 8.4 support **roles** (verified) (named collections of privileges) that can be created/dropped, granted/revoked privileges, and granted/revoked to user accounts. Active roles for an account can be selected and changed during sessions:

```sql
CREATE ROLE 'app_developer', 'app_read', 'app_write';
```

RDS for MySQL 8 also adds user account categories — system vs. regular users distinguished by the `SYSTEM_USER` privilege:

```sql
CREATE USER u1 IDENTIFIED BY 'password';
GRANT ALL ON *.* TO u1 WITH GRANT OPTION;
-- GRANT ALL includes SYSTEM_USER, so at this point
-- u1 can manipulate system or regular accounts
```

Syntax:

```sql
CREATE USER <user> [<authentication options>] [REQUIRE {NONE | <TLS options>] }]
[WITH <resource options> ] [<Password options> | <Lock options>]

-- <Authentication option>:
-- {IDENTIFIED BY 'auth string' | PASSWORD 'hash string' | WITH auth plugin
--  | auth plugin BY 'auth_string' | auth plugin AS 'hash string'}
-- <TLS options>: {SSL | X509 | CIPHER 'cipher' | ISSUER 'issuer' | SUBJECT 'subject'}
-- <Resource options>: {MAX_QUERIES_PER_HOUR | MAX_UPDATES_PER_HOUR
--  | MAX_CONNECTIONS_PER_HOUR | MAX_USER_CONNECTIONS count}
-- <Password options>: {PASSWORD EXPIRE | DEFAULT | NEVER | INTERVAL N DAY}
-- <Lock options>: {ACCOUNT LOCK | ACCOUNT UNLOCK}
```

> In Aurora MySQL you can assign resource limitations to specific users, similar to the SQL Server Resource Governor.

Examples:

```sql
-- Create a user, force a password change, and impose resource limits
CREATE USER 'Dan'@'localhost'
IDENTIFIED WITH mysql_native_password BY 'User''sPasswordEXAMPLE'
WITH MAX_QUERIES_PER_HOUR 500
PASSWORD EXPIRE;

-- Create a user with IAM authentication
CREATE USER LocalUser
IDENTIFIED WITH AWSAuthenticationPlugin AS 'RDS';   -- the AS value is the literal 'RDS'; the user name must match the IAM policy's dbuser
```

## Summary

| Task | SQL Server | Aurora MySQL |
|---|---|---|
| View database users | `SELECT Name FROM sys.sysusers` | `SELECT User FROM mysql.user` |
| Create a user and password | `CREATE USER <User Name> WITH PASSWORD = <PassWord>;` | `CREATE USER <User Name> IDENTIFIED BY <Password>` |
| Create a role | `CREATE ROLE <Role Name>` | `CREATE ROLE <Role Name>` (3 / 8.4) |
| Change a user's password | `ALTER LOGIN <SQL Login> WITH PASSWORD = <PassWord>;` | `ALTER USER <User Name> IDENTIFIED BY <Password>` |
| External authentication | Windows Authentication | AWS IAM (Identity and Access Management) |
| Add a user to a role | `ALTER ROLE <Role Name> ADD MEMBER <User Name>` | `GRANT <Role> TO <User>; SET DEFAULT ROLE ALL TO <User>;` |
| Lock a user | `ALTER LOGIN <Login Name> DISABLE` | `ALTER User <User Name> ACCOUNT LOCK` |
| Grant SELECT on a schema | `GRANT SELECT ON SCHEMA::<Schema Name> to <User Name>` | `GRANT SELECT ON <Schema Name>.* TO <User Name>` |

## Conversion notes
- SQL Server's two-tier model (server Logins + database Users) collapses to a single Aurora MySQL **User** that combines authentication and authorization. MySQL users include a host part (`'user'@'host'`).
- A SQL Server database == an Aurora MySQL **database/schema**.
- Map SQL Server database roles to MySQL roles. **Granted roles are inactive by default** (`activate_all_roles_on_login` is OFF, verified): run `SET DEFAULT ROLE ALL TO user` after granting (verified), or the user sees none of the role's privileges.
- Fixed database roles: `db_datareader` → `GRANT SELECT ON db.* TO role`; `db_datawriter` → `INSERT, UPDATE, DELETE`; `db_ddladmin` → `CREATE, ALTER, DROP, INDEX, CREATE VIEW, CREATE ROUTINE, ALTER ROUTINE, TRIGGER`; `db_owner` → `ALL ON db.*`. The Aurora master user holds `rds_superuser_role`, not `SUPER` (verified) — the closest to `sysadmin`, with limits (no `SET GLOBAL`, resource groups).
- **Authentication plugins:** new users get `caching_sha2_password` on Aurora MySQL 8.4 and `mysql_native_password` on 3.x (verified). The `IDENTIFIED WITH mysql_native_password` example above still works on 8.4 but is discouraged; drivers must support `caching_sha2_password`.
- Password policy (≈ `CHECK_POLICY`/`CHECK_EXPIRATION`): `PASSWORD EXPIRE INTERVAL n DAY`, `FAILED_LOGIN_ATTEMPTS n PASSWORD_LOCK_TIME d`, `PASSWORD HISTORY n` all work on both versions (verified); 8.4 also has the `validate_password` component (policy MEDIUM, verified). `CREATE USER x` without a password is still accepted (verified) — forbid it in review.
- Windows/Active Directory authentication → IAM database authentication, or Kerberos via AWS Directory Service where supported for the engine version.
- Windows Authentication → AWS IAM database authentication (token-based, SSL-encrypted, 15-min token lifetime, 20 new connections/sec limit).
- Built-in SQL Server roles (`db_datareader`, `db_owner`, etc.) have no direct equivalent; reproduce them as explicit privilege grants or IAM roles.
- SQL Server resource governance maps to MySQL per-user resource options (`MAX_QUERIES_PER_HOUR`, etc.).
- The `dbo` schema and sysadmin-mapped users generally don't need migration.
