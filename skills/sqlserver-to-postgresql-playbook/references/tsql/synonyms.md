# Synonyms

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.synonyms.html

**Conversion category:** Manual (two-star feature compatibility, no automation — workaround available)
**SCT automation:** No automation; N/A action code

## SQL Server

Synonyms are alternative identifiers for other database objects (the base object), which can reside in the same database, another database on the same instance, or a remote server. They provide an abstraction layer isolating client code from changes to the name/location of the base object, and simplify four-part identifiers when accessing remote instances.

Example use case: table A is moved from server A to server B for scale-out; without synonyms, client code must be rewritten. Create a synonym `Table A` to transparently redirect to server B with no code changes.

Synonyms can be created for: CLR/assembly procedures and functions, replication-filter-procedures, extended stored procedures, SQL scalar/table-valued/inline-table-valued functions, views, stored procedures, and user-defined tables (incl. temporary tables).

Syntax:

```sql
CREATE SYNONYM [ <Synonym Schema> ] . <Synonym Name>
FOR [ <Server Name> ] . [ <Database Name> ] . [ Schema Name> ] . <Object Name>
```

Examples:

```sql
-- Local object in a separate database:
CREATE TABLE DB1.Schema1.MyTable
( KeyColumn INT IDENTITY PRIMARY KEY, DataColumn VARCHAR(20) NOT NULL );
USE DB2;
CREATE SYNONYM Schema2.MyTable FOR DB1.Schema1.MyTable

-- Remote object (linked server ServerA on Server B):
USE DB2;
CREATE SYNONYM Schema2.MyTable FOR ServerA.DB1.Schema1.MyTable;
```

## PostgreSQL

PostgreSQL has **no synonym feature**, but you can emulate it. AWS SCT converts multiple source databases into one target database, with each source database becoming a schema (source schema prefixed to the target schema name) — so if you migrate several databases in one project, you can often avoid synonyms entirely (all objects are in the same database). Ensure the database user has privileges on the base object.

**Synonym for a table → use a view:**

```sql
CREATE TABLE target_db_name.DB1_Schema1.MyTable
( KeyColumn NUMERIC PRIMARY KEY, DataColumn VARCHAR(20) NOT NULL );

CREATE VIEW target_db_name.DB2_Schema2.MyTable_Syn
AS SELECT * FROM target_db_name.DB1_Schema1.MyTable
```

**Synonym for a user-defined type → wrap with another type:**

```sql
CREATE TYPE DB1.Schema1.MyType AS (
ID NUMERIC,
name CHARACTER VARYING(100));

CREATE TYPE DB2.Schema2.MyType_Syn AS (
udt DB1.Schema1.MyT);
```

**Synonym for a function → wrap with another function:**

```sql
CREATE OR REPLACE FUNCTION DB1.Schema1.MyFunc (P_NUM NUMERIC)
RETURNS numeric AS $$
begin
  RETURN P_NUM * 2;
END; $$
LANGUAGE PLPGSQL;

CREATE OR REPLACE FUNCTION DB2.Schema2.MyFunc_Syn (P_NUM NUMERIC)
RETURNS numeric AS $$
begin
  RETURN DB1.Schema1.MyFunc(P_NUM);
END; $$
LANGUAGE PLPGSQL;
```

## Conversion notes
- No native synonyms — emulate per object type: views for tables/views, wrapper types for UDTs, wrapper functions for functions.
- Consolidating multiple source databases into one target database (SCT default) often removes the need for synonyms.
- This is a manual conversion dimension; verify privileges on base objects.
- Cross-server (remote) synonyms have no direct equivalent — rely on consolidated schemas or foreign data wrappers (e.g., postgres_fdw).
