# Synonyms for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.synonyms.html

**Conversion category:** Blocked (One star feature compatibility — not supported, no generic workaround)
**SCT automation:** No automation

## SQL Server

Synonyms are alternative identifiers for other database objects (the *base object*), which may reside in the same database, another database on the instance, or a remote server. They provide an abstraction layer isolating application code from changes to the base object's name or location — often used to simplify four-part identifiers when accessing remote instances (e.g. transparently redirecting from Server A to Server B without code changes).

Can create synonyms for: assembly/SQL stored procedures, table-valued/scalar/aggregate/inline functions, replication filter procedures, extended stored procedures, views, and user-defined tables (including local/global temp tables).

### Syntax

```sql
CREATE SYNONYM [ <Synonym Schema> ] . <Synonym Name>
FOR [ <Server Name> ] . [ <Database Name> ] . [ <Schema Name> ] . <Object Name>
```

### Examples

```sql
-- Synonym for a local object in another database
CREATE TABLE DB1.Schema1.MyTable
(
    KeyColumn INT IDENTITY PRIMARY KEY,
    DataColumn VARCHAR(20) NOT NULL
);
USE DB2;
CREATE SYNONYM Schema2.MyTable
FOR DB1.Schema1.MyTable;

-- Synonym for a remote object (via linked server on Server B → Server A)
USE DB2;
CREATE SYNONYM Schema2.MyTable
FOR ServerA.DB1.Schema1.MyTable;
```

## MySQL

Aurora MySQL does **not** support synonyms, and there is no known generic workaround.

Partial workarounds:
- For tables/views: use encapsulating **views** as an abstraction layer.
- Use **functions or stored procedures** that call other functions/stored procedures.

## Conversion notes

- No direct equivalent — abstraction must be rebuilt with views and/or stored routines.
- Synonyms are often paired with linked servers, which Aurora MySQL also does not support — cross-instance access must be handled at the application level.
