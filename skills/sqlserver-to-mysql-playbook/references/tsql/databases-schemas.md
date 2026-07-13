# Databases and schemas for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.databasesschemas.html

**Conversion category:** Manual (Two star feature compatibility)
**SCT automation:** Two star automation level

## SQL Server

Databases and schemas are logical containers for security/access control. Security at three levels: objects, schemas (collections of objects), databases (collections of schemas). Each instance hosts multiple databases plus system DBs (Master, Model, TempDB, MSDB). Built-in security schemas: `guest`, `dbo`, `db_datareader`, `sys`, `INFORMATION_SCHEMA`, etc.

Unique object identifiers use **three-part** names: `<Database>.<Schema>.<Object>`. View databases via `sys.databases`.

### Syntax

```sql
CREATE DATABASE <database name>
[ ON [ PRIMARY ] <file specifications>[,<filegroup>]
[ LOG ON <file specifications>
[ WITH <options specification> ] ;

CREATE SCHEMA <schema name> | AUTHORIZATION <owner name>;
```

### Examples

```sql
USE master;
ALTER DATABASE NewDB ADD FILEGROUP NewGroup;
ALTER DATABASE NewDB
ADD FILE ( NAME = 'NewFile', FILENAME = 'D:\NewFile.ndf', SIZE = 2 MB )
TO FILEGROUP NewGroup;
USE NewDB;
CREATE TABLE NewTable ( Col1 INT PRIMARY KEY ) ON NewGroup;

-- new schema + database
CREATE DATABASE NewDB;
USE NewDB;
CREATE SCHEMA NewSchema;
CREATE TABLE NewSchema.NewTable
( NewColumn VARCHAR(20) NOT NULL PRIMARY KEY );
```

## MySQL

Aurora MySQL supports `CREATE SCHEMA` and `CREATE DATABASE` — **synonymous**. No concept of an instance hosting multiple databases each containing multiple schemas. Objects use **two-part** names: `<schema>.<object>` (database = schema conceptually). Each database/schema is a separate set of physical files. No schema owner concept — permissions granted explicitly. Supports default collation at schema level (SQL Server only at database level).

`USE <database name>;` works identically to SQL Server.

### Syntax

```sql
CREATE {DATABASE | SCHEMA} <database name>
[DEFAULT] CHARACTER SET [=] <character set>|
[DEFAULT] COLLATE [=] <collation>
```

### Examples

```sql
CREATE DATABASE NewDatabase;
USE NewDatabase;
CREATE TABLE NewTable ( NewColumn VARCHAR(20) NOT NULL PRIMARY KEY );
INSERT INTO NewTable VALUES('NewValue');
SELECT * FROM NewTable;

-- view databases/schemas
SHOW DATABASES;

-- create-database reminder
SHOW CREATE DATABASE Demo;
-- Demo  CREATE DATABASE `Demo` /*!40100 DEFAULT CHARACTER SET latin1 */
```

## Conversion notes

- Schema and database are synonymous in Aurora MySQL; three-part names collapse to two-part.
- Rewrite `MyDB..MyTable` → `MyDB.MyTable` (replace the double dot caused by omitted schema with a single dot).
- Consider creating a `dbo` schema in Aurora MySQL to minimize code changes when SQL Server code uses `dbo.<object>`.
- Applications needing both multiple databases AND multiple schemas require **multiple Aurora instances** with cross-instance connectivity handled at the application layer.

| Current architecture | Migrate to | Rewrites |
|---|---|---|
| Single DB, all objects in `dbo` | Single instance, single DB/schema | If using `dbo.<object>`, create a `dbo` schema to minimize changes |
| Single DB, multiple schemas | Single instance, multiple DBs/schemas | No hierarchy rewrites needed |
| Multiple DBs, all in `dbo` | Single instance, multiple DBs/schemas | Rewrite `MyDB..MyTable` → `MyDB.MyTable` |
| Multiple DBs, multiple schemas | Multiple instances | Cross-instance connectivity at application level |
