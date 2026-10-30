# Synonyms for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.synonyms.html

**Conversion category:** Blocked (One star feature compatibility — not supported, no generic workaround)
**SCT automation:** No automation

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Still no synonyms; updatable view synonyms (verified), database-qualified names, wrapper routines.

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
- Still no `CREATE SYNONYM` on Aurora MySQL 3 / 8.4. A single-table view is updatable, so `INSERT`/`UPDATE`/`DELETE` through a "synonym view" work (verified on both versions); recreate the view after base-table column changes (`SELECT *` is expanded at creation).
- Synonyms pointing to another database in the same instance → a database-qualified name (`otherdb.table`) or a view in the local database; cross-database joins work in one cluster.
- Synonyms for procedures/functions → wrapper routines that `CALL`/return the target (no overloading or defaults, see `stored-procedures.md`).
