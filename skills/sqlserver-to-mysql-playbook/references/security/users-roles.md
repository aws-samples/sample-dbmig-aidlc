# Users and Roles

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.security.usersroles.html

**Conversion category:** Manual
**SCT automation:** N/A (two-star feature compatibility; no native role support — use AWS IAM accounts with the AWS Authentication Plugin)

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

Aurora MySQL supports only **Users**; Roles aren't supported (in the base engine). Administrators specify privileges for individual users. Aurora MySQL uses database user accounts to authenticate sessions and authorize access to objects. Wildcards can specify multiple privileges for multiple objects.

> In Aurora MySQL, a database is equivalent to a SQL Server schema.

With **IAM database authentication**, roles are available as part of the IAM framework. Authentication uses tokens instead of passwords — AWS Signature Version 4 generates tokens with a 15-minute lifetime, so user credentials need not be stored in the database. IAM can be used alongside standard database authentication. The **AWS Authentication Plugin** lets IAM-account users authenticate with access tokens, similar to SQL Server Windows Authentication.

IAM database authentication benefits:
- Supports roles for simplifying user/access management.
- Single sign-on, safer than MySQL-managed passwords.
- Encrypts network traffic with SSL.
- Centrally managed access to database resources.

> IAM database authentication limits new connections to 20 connections/second.

Amazon RDS for MySQL 8 supports **roles** (named collections of privileges) that can be created/dropped, granted/revoked privileges, and granted/revoked to user accounts. Active roles for an account can be selected and changed during sessions:

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
IDENTIFIED WITH AWSAuthenticationPlugin AS 'IAMUser';
```

## Summary

| Task | SQL Server | Aurora MySQL |
|---|---|---|
| View database users | `SELECT Name FROM sys.sysusers` | `SELECT User FROM mysql.user` |
| Create a user and password | `CREATE USER <User Name> WITH PASSWORD = <PassWord>;` | `CREATE USER <User Name> IDENTIFIED BY <Password>` |
| Create a role | `CREATE ROLE <Role Name>` | Use AWS IAM Roles |
| Change a user's password | `ALTER LOGIN <SQL Login> WITH PASSWORD = <PassWord>;` | `ALTER USER <User Name> IDENTIFIED BY <Password>` |
| External authentication | Windows Authentication | AWS IAM (Identity and Access Management) |
| Add a user to a role | `ALTER ROLE <Role Name> ADD MEMBER <User Name>` | Use AWS IAM Roles |
| Lock a user | `ALTER LOGIN <Login Name> DISABLE` | `ALTER User <User Name> ACCOUNT LOCK` |
| Grant SELECT on a schema | `GRANT SELECT ON SCHEMA::<Schema Name> to <User Name>` | `GRANT SELECT ON <Schema Name>.* TO <User Name>` |

## Conversion notes
- SQL Server's two-tier model (server Logins + database Users) collapses to a single Aurora MySQL **User** that combines authentication and authorization. MySQL users include a host part (`'user'@'host'`).
- A SQL Server database == an Aurora MySQL **database/schema**.
- **No native roles** in the base Aurora MySQL engine — replicate role-based design with AWS IAM roles + the AWS Authentication Plugin, or use RDS for MySQL 8 native roles where available.
- Windows Authentication → AWS IAM database authentication (token-based, SSL-encrypted, 15-min token lifetime, 20 new connections/sec limit).
- Built-in SQL Server roles (`db_datareader`, `db_owner`, etc.) have no direct equivalent; reproduce them as explicit privilege grants or IAM roles.
- SQL Server resource governance maps to MySQL per-user resource options (`MAX_QUERIES_PER_HOUR`, etc.).
- The `dbo` schema and sysadmin-mapped users generally don't need migration.
