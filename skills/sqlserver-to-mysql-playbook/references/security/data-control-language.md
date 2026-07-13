# Data Control Language (DCL)

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.security.datacontrollanguage.html

**Conversion category:** Assisted
**SCT automation:** N/A (No automation; four-star feature compatibility)

## SQL Server

The ANSI standard uses `GRANT` and `REVOKE` to control permissions. SQL Server also provides a `DENY` command to explicitly restrict access. `DENY` takes precedence over `GRANT` and avoids conflicting permissions for users with multiple logins (e.g. a user `DENY`'d through group membership but `GRANT`'d via a personal login is denied access).

SQL Server allows granting permissions at multiple levels — from lower-level objects (columns) to higher-level objects (servers). Permissions are categorized for specific services/features (e.g. the service broker) and are used together with database users and roles.

Syntax:

```sql
GRANT { ALL [ PRIVILEGES ] } | <permission> [ ON <securable> ] TO <principal>

DENY { ALL [ PRIVILEGES ] } | <permission> [ ON <securable> ] TO <principal>

REVOKE [ GRANT OPTION FOR ] {[ ALL [ PRIVILEGES ] ]|<permission>} [ ON <securable> ] { TO | FROM } <principal>
```

## MySQL

Aurora MySQL supports the ANSI DCL commands `GRANT` and `REVOKE`. Administrators can grant/revoke permissions for individual objects (column, stored function, table) and can use wildcards to target multiple objects.

Only explicitly granted permissions can be revoked. For example, after:

```sql
GRANT SELECT
ON database.*
TO UserX;
```

You cannot `REVOKE` the permission for a single table. Instead revoke for all tables:

```sql
REVOKE SELECT
ON database.*
FROM UserX;
```

Aurora MySQL provides a `GRANT` option similar to SQL Server's `WITH GRANT OPTION`, letting a user further grant the same permission to others:

```sql
GRANT EXECUTE
ON PROCEDURE demo.Procedure1
TO UserY
WITH GRANT OPTION;
```

Aurora MySQL users can have resource restrictions on their accounts, similar to the SQL Server Resource Governor.

Aurora MySQL privileges include:

| Permission | Use to |
|---|---|
| `ALL [PRIVILEGES]` | Grant all privileges at the specified access level except `GRANT OPTION` and `PROXY`. |
| `ALTER` | Enable use of `ALTER TABLE`. Levels: Global, database, table. |
| `ALTER ROUTINE` | Enable stored routines to be altered/dropped. Levels: Global, database, procedure. |
| `CREATE` | Enable database and table creation. Levels: Global, database, table. |
| `CREATE ROUTINE` | Enable stored routine creation. Levels: Global, database. |
| `CREATE TEMPORARY TABLES` | Enable use of `CREATE TEMPORARY TABLE`. Levels: Global, database. |
| `CREATE USER` | Enable `CREATE USER`, `DROP USER`, `RENAME USER`, `REVOKE ALL PRIVILEGES`. Level: Global. |
| `CREATE VIEW` | Enable views to be created/altered. Levels: Global, database, table. |
| `DELETE` | Enable use of `DELETE`. Levels: Global, database, table. |
| `DROP` | Enable databases, tables, views to be dropped. Levels: Global, database, table. |
| `EVENT` | Enable events for the Event Scheduler. Levels: Global, database. |
| `EXECUTE` | Enable the user to run stored routines. Levels: Global, database, table. |
| `GRANT OPTION` | Enable privileges to be granted/removed from other accounts. Levels: Global, database, table, procedure, proxy. |
| `INDEX` | Enable indexes to be created/dropped. Levels: Global, database, table. |
| `INSERT` | Enable use of `INSERT`. Levels: Global, database, table, column. |
| `LOCK TABLES` | Enable `LOCK TABLES` on tables with `SELECT` privilege. Levels: Global, database. |
| `PROXY` | Enable user proxying. Level: From user to user. |
| `REFERENCES` | Enable foreign key creation. Levels: Global, database, table, column. |
| `REPLICATION CLIENT` | Enable the user to determine the location of primary/secondary servers. Level: Global. |
| `REPLICATION SLAVE` | Enable replication replicas to read binary log events from the primary. Level: Global. |
| `SELECT` | Enable use of `SELECT`. Levels: Global, database, table, column. |
| `SHOW DATABASES` | Enable `SHOW DATABASES` to show all databases. Level: Global. |
| `SHOW VIEW` | Enable use of `SHOW CREATE VIEW`. Levels: Global, database, table. |
| `TRIGGER` | Enable trigger operations. Levels: Global, database, table. |
| `UPDATE` | Enable use of `UPDATE`. Levels: Global, database, table, column. |

Syntax:

```sql
GRANT <privilege type>...
ON [object type] <privilege level>
TO <user> ...

REVOKE <privilege type>...
ON [object type] <privilege level>
FROM <user> ...
```

(Table, Function, and Procedure object types can be explicitly stated but aren't mandatory.)

Examples:

```sql
-- Attempt to REVOKE a partial permission that was granted as a wildcard
CREATE USER TestUser;
GRANT SELECT
    ON Demo.*
    TO TestUser;
REVOKE SELECT ON Demo.Invoices
    FROM TestUser
-- SQL ERROR [1147][42000]: There is no such grant defined for user TestUser
-- on host '%' on table 'Invoices'

-- Grant SELECT to a user on all tables in the demo database
GRANT SELECT
ON Demo.*
TO 'user'@'localhost';

-- Revoke EXECUTE on the EmployeeReport stored procedure
REVOKE EXECUTE
ON Demo.EmployeeReport
FROM 'user'@'localhost';
```

## Conversion notes
- `GRANT` and `REVOKE` map closely between the two engines (ANSI-standard).
- **No `DENY` in MySQL.** SQL Server `DENY` (which overrides `GRANT`) has no equivalent and must be reworked by not granting the permission in the first place.
- SQL Server's `WITH GRANT OPTION` maps directly to MySQL's `WITH GRANT OPTION`.
- MySQL revokes only exactly what was granted: you cannot revoke a single table's permission if it was granted with a wildcard (`db.*`). Revoke at the same granularity it was granted.
- MySQL user identity includes host (`'user'@'localhost'`), unlike SQL Server principals.
- MySQL accounts can carry resource restrictions, analogous to SQL Server Resource Governor.
