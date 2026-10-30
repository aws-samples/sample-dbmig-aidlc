# Linked servers

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.management.linkedservers.html

**Conversion category:** Manual (No feature compatibility)
**SCT automation:** No automation

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): FEDERATED unavailable and silently substituted (verified), practical replacements, OPENROWSET BULK → LOAD DATA FROM S3, no distributed transactions.

## SQL Server

Linked servers let the database engine connect to external OLE-DB sources to run T-SQL against tables in other SQL Server instances or other RDBMS engines (Oracle, Access, Excel, text files, etc.). Benefits:
* Reading external data for import/processing.
* Running distributed queries, modifications, and transactions across enterprise data sources.
* Querying heterogeneous data sources with the familiar T-SQL API.

The linked server definition contains the alias, the OLE-DB provider (a .NET DLL handling interaction with a source type), and connection parameters for the specific OLE-DB data source. SQL Server parses T-SQL accessing the linked server and sends requests to the provider.

Management via SSMS or system stored procedures:
* `sp_addlinkedserver` — add server definitions.
* `sp_addlinkedserverlogin` — define security context.
* `sp_linkedservers` or `SELECT * FROM sys.servers` — retrieve metadata.
* `sp_dropserver` — delete a linked server.

Access uses a four-part name: `<Server Name>.<Database Name>.<Schema Name>.<Object Name>`. The `OPENQUERY` function invokes pass-through queries; `OPENROWSET`/`OPENDATASOURCE` allow one-time remote access without a predefined linked server.

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

Examples:

```sql
-- Linked server to a local text file
EXECUTE sp_addlinkedserver MyTextLinkedServer, N'Jet 4.0',
    N'Microsoft.Jet.OLEDB.4.0',
    N'D:\TextFiles\MyFolder',
    NULL,
    N'Text';

-- Define security context
EXECUTE sp_addlinkedsrvlogin MyTextLinkedServer, FALSE, Admin, NULL;

-- List tables in the folder
EXEC sp_tables_ex MyTextLinkedServer;

-- SELECT using a four-part name
SELECT *
FROM MyTextLinkedServer...[FileName#text];
```

## MySQL

Aurora MySQL doesn't support remote data access. Connectivity between schemas is trivial, but connectivity to other instances requires a **custom application solution**.

## Conversion notes
- No equivalent — Aurora MySQL has no linked-server / OLE-DB distributed query capability and no SCT automation.
- Cross-schema queries work natively on the same instance.
- Cross-instance / heterogeneous access must be re-implemented in the application layer (e.g., application code that connects to each source), or by consolidating data via AWS DMS / AWS Glue.
- The `FEDERATED` engine is not available on Aurora (verified); `CREATE TABLE … ENGINE=FEDERATED` silently creates a local InnoDB table, even with `NO_ENGINE_SUBSTITUTION` (verified on 3.13 and 8.4.8). Check `information_schema.tables.ENGINE` after applying converted DDL.
- Practical replacements: consolidate the linked databases into one Aurora cluster (cross-database `db.table` joins work); replicate remote tables into the cluster with AWS DMS or binlog replication; query across engines with Amazon Athena federated queries; call a Lambda function (`lambda_sync()`) for occasional remote lookups.
- `OPENQUERY`/`OPENROWSET`/four-part names → none; `OPENROWSET(BULK …)` → `LOAD DATA FROM S3`.
- Distributed transactions (`BEGIN DISTRIBUTED TRANSACTION`, MSDTC) → none; redesign as idempotent steps or sagas.
