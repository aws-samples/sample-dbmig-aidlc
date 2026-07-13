# Linked servers

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.linkedservers.html

**Conversion category:** N/A (three-star feature compatibility)
**SCT automation:** SCT action code index: Linked Servers

Key difference: Syntax and option differences, similar functionality.

## SQL Server

Linked servers let the database engine connect to external OLE-DB sources to run T-SQL commands against tables in other SQL Server instances or other RDBMS engines (Oracle), and sources such as Access, Excel, and text files.

Benefits: read external data; run distributed queries, modifications, and transactions; query heterogeneous sources with the familiar T-SQL API.

Configure via SSMS or `sp_addlinkedserver`. A definition holds the alias, the OLE-DB provider (a .NET DLL handling interaction with that source type), and connection parameters. Management procedures:
- `sp_addlinkedserver` — add server definitions.
- `sp_addlinkedserverlogin` — define security context.
- `sp_linkedservers` or `SELECT * FROM sys.servers` — retrieve metadata.
- `sp_dropserver` — delete a linked server.

Access data via a four-part name `<Server>.<Database>.<Schema>.<Object>`, or with `OPENQUERY` (pass-through), `OPENROWSET`/`OPENDATASOURCE` (one-time access).

Syntax:

```sql
EXECUTE sp_addlinkedserver
    [ @server= ] <Linked Server Name>
    [ , [ @srvproduct= ] <Product Name>]
    [ , [ @provider= ] <OLE DB Provider>]
    [ , [ @datasrc= ] <Data Source>]
    [ , [ @location= ] <Data Source Address>]
    [ , [ @provstr= ] <Provider Connection String>]
    [ , [ @catalog= ] <Database>];
```

Example — linked server to a local text file:

```sql
EXECUTE sp_addlinkedserver MyTextLinkedServer, N'Jet 4.0',
    N'Microsoft.Jet.OLEDB.4.0', N'D:\TextFiles\MyFolder', NULL, N'Text';

EXECUTE sp_addlinkedsrvlogin MyTextLinkedServer, FALSE, Admin, NULL;  -- security context
EXEC sp_tables_ex MyTextLinkedServer;  -- list tables

SELECT * FROM MyTextLinkedServer...[FileName#text];  -- four-part name query
```

## PostgreSQL

Querying remote databases is available via two options:
- `dblink` database link function.
- Foreign data wrapper (FDW) `postgres_fdw` extension (newer, closer to the SQL standard, often better performance).

Examples (`dblink`):

```sql
-- Load the extension
CREATE EXTENSION dblink;

-- Create a persistent named connection
SELECT dblink_connect('myconn',
    'dbname=postgres port=5432 host=hostname user=username password=password');

-- Run a query via the named connection (must declare result columns/types)
SELECT * FROM dblink('myconn', 'SELECT id, name FROM EMPLOYEES') AS p(id int, fullname text);

-- Close the connection
SELECT dblink_disconnect('myconn');

-- Alternatively, pass the full connection string inline
SELECT * FROM dblink(
    'dbname=postgres port=5432 host=hostname user=username password=password',
    'SELECT id, name FROM EMPLOYEES') AS p(id int, fullname text);

-- DML on remote tables
SELECT * FROM dblink('myconn', $$INSERT into employees VALUES (3,'New Employees No. 3!')$$) AS t(message text);
SELECT * FROM dblink('myconn', $$DELETE FROM employees WHERE id=3$$) AS t(message text);

-- Create a local table from remote data
SELECT emps.* INTO new_employees_table
    FROM dblink('myconn', 'SELECT * FROM employees') AS emps(id int, name varchar);

-- Join remote data with local data
SELECT local_emps.id, local_emps.name, s.sale_year, s.sale_amount
    FROM local_emps
    INNER JOIN dblink('myconn', 'SELECT * FROM working_hours') AS s(id int, hours_worked int)
    ON local_emps.id = s.id;

-- Run DDL on the remote database
SELECT * FROM dblink('myconn', $$CREATE table new_remote_tbl (a int, b text)$$) AS t(a text);
```

## Conversion notes

- Similar functionality, different syntax — replace linked servers / four-part names / `OPENQUERY` with `dblink` or `postgres_fdw`.
- `dblink` requires declaring the result column list and types for each query; `postgres_fdw` defines foreign tables once and queries them like local tables (preferred for standards alignment and performance).
- SCT flags linked servers (action code index "Linked Servers") for manual review during conversion.
