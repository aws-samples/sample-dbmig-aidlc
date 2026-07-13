# Configuring Database Options

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.configuration.databaseoptions.html

**Conversion category:** N/A (One-star feature compatibility)
**SCT automation:** N/A

## SQL Server

SQL Server provides database-level options set with `ALTER DATABASE … SET`. Use these to:
- Set default session options (see Session Options).
- Enable/disable database features such as `SNAPSHOT_ISOLATION`, `CHANGE_TRACKING`, and `ENABLE_BROKER`.
- Configure high availability / disaster recovery (e.g. Always On availability groups).
- Configure security access control — restrict to a single user, set the database offline, or set read-only.

### Syntax

```sql
ALTER DATABASE { <database name> } SET { <option> [ ,...n ] };
```

### Examples

```sql
-- Set read-only and use ARITHABORT by default
ALTER DATABASE Demo SET READ_ONLY, ARITHABORT ON;

-- Use automatic statistic creation
ALTER DATABASE Demo SET AUTO_CREATE_STATISTICS ON;

-- Set a database offline immediately
ALTER DATABASE DEMO SET OFFLINE WITH ROLLBACK IMMEDIATE;
```

## PostgreSQL

Aurora PostgreSQL supports `CREATE SCHEMA` and `CREATE DATABASE` statements. As with SQL Server, an instance hosts multiple databases, which contain multiple schemas. Objects use a three-part name: `<database>.<schema>.<object>`.

Database options correspond to cluster-level parameters managed by AWS **Cluster Parameter Groups**. Some SQL Server equivalent parameters exist at the instance level in the AWS **Database Parameter Group**.

Example — create a database and schema:

```sql
CREATE DATABASE myapp;
CREATE SCHEMA sales;
```

## Conversion notes
- Database options map to AWS **Database Parameter Group**; server options map to AWS **Cluster Parameter Group** (see Server Options).
- There is no direct `ALTER DATABASE … SET` equivalent — feature/behavior settings are managed through parameter groups rather than per-database T-SQL.
- Aurora PostgreSQL uses three-part naming `<database>.<schema>.<object>`, mirroring SQL Server's database/schema/object hierarchy.
