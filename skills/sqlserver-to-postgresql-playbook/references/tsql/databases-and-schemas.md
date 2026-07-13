# Databases and Schemas

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.schemas.html

**Conversion category:** Automatic (five-star feature compatibility, five-star automation)
**SCT automation:** Five-star automation level; N/A action code

## SQL Server

Databases and schemas are logical containers for security/access control. Security exists at three levels: objects, schemas (collections of objects), databases (collections of schemas). Built-in security schemas (`guest`, `dbo`, `db_datareader`, `sys`, `INFORMATION_SCHEMA`) usually need not be migrated.

Each instance hosts databases plus system databases (Master, Model, TempDB, MSDB). Objects use three-part identifiers: `<Database>.<Schema>.<Object>`. Use ANSI information schema views to inspect metadata; `sys.databases` lists databases.

Syntax:

```sql
CREATE DATABASE <database name>
[ ON [ PRIMARY ] <file specifications>[,<filegroup>]
[ LOG ON <file specifications>
[ WITH <options specification> ] ;

CREATE SCHEMA <schema name> | AUTHORIZATION <owner name>;
```

Examples:

```sql
-- Add file/filegroup and create table on it:
USE master;
ALTER DATABASE NewDB ADD FILEGROUP NewGroup;
ALTER DATABASE NewDB ADD FILE (
  NAME = 'NewFile', FILENAME = 'D:\NewFile.ndf', SIZE = 2 MB
) TO FILEGROUP NewGroup;
USE NewDB;
CREATE TABLE NewTable ( Col1 INT PRIMARY KEY ) ON NewGroup;

SELECT Name FROM sys.databases WHERE database_id > 4;

-- Create table within a new schema and database:
USE master
CREATE DATABASE NewDB;
USE NewDB;
CREATE SCHEMA NewSchema;
CREATE TABLE NewSchema.NewTable ( NewColumn VARCHAR(20) NOT NULL PRIMARY KEY );
```

## PostgreSQL

Aurora PostgreSQL supports `CREATE SCHEMA` and `CREATE DATABASE`. An instance hosts multiple databases, each containing multiple schemas. Objects use three-part names: `<database>.<schema>.<object>`. A schema is a namespace of named objects. A new database is cloned from a template.

Syntax:

```sql
CREATE DATABASE name
  [ [ WITH ] [ OWNER [=] user_name ]
    [ TEMPLATE [=] template ]
    [ ENCODING [=] encoding ]
    [ LC_COLLATE [=] lc_collate ]
    [ LC_CTYPE [=] lc_ctype ]
    [ TABLESPACE [=] tablespace_name ]
    [ ALLOW_CONNECTIONS [=] allowconn ]
    [ CONNECTION LIMIT [=] connlimit ]
    [ IS_TEMPLATE [=] istemplate ] ]

CREATE SCHEMA schema_name [ AUTHORIZATION role_specification ] [ schema_element [ ... ] ]
CREATE SCHEMA AUTHORIZATION role_specification [ schema_element [ ... ] ]
CREATE SCHEMA IF NOT EXISTS schema_name [ AUTHORIZATION role_specification ]
-- role_specification: user_name | CURRENT_USER | SESSION_USER
```

View databases:

```sql
SELECT datname, datcollate, datistemplate, datallowconn
FROM postgres.pg_catalog.pg_database;
```

Examples:

```sql
CREATE DATABASE NewDatabase;

CREATE SCHEMA AUTHORIZATION joe;

CREATE SCHEMA world_flights
  CREATE TABLE flights (flight_id VARCHAR(10), departure DATE, airport VARCHAR(30))
  CREATE VIEW us_flights AS
    SELECT flight_id, departure FROM flights WHERE airport='United States';
```

## Conversion notes
- Both engines use the instance → database → schema → object hierarchy with three-part names — high compatibility.
- **No `USE` command in PostgreSQL**: cannot switch default database within a session. To use a different database, open a new connection. Cross-database object references aren't supported as in SQL Server.
- Applications using a single database with multiple schemas migrate with fewer rewrites (two-part names already in use).
- Built-in SQL Server schemas (`dbo`, `sys`, etc.) generally don't need migration; objects in `dbo` typically map to the PostgreSQL `public` schema or a named schema.
- PostgreSQL has no filegroup concept; ignore SQL Server file/filegroup management during conversion (use tablespaces if needed).
