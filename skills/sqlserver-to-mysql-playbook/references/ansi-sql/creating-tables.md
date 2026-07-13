# Creating Tables for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.creatingtables.html

**Conversion category:** Assisted (Four star feature compatibility)
**SCT automation:** Four star automation level

**Key differences:** `IDENTITY` vs `AUTO_INCREMENT`. Primary key is always clustered. `CREATE TEMPORARY TABLE` syntax. Unsupported `@table` variables.

## SQL Server

`CREATE TABLE` conforms to ANSI/ISO entry level. Defines table/schema/db names, columns, data types, column/table constraints, defaults, and PK/UK/FK.

### T-SQL Extensions
Index types (clustered/non-clustered) with properties like `FILLFACTOR`, `ON <File Group>` storage, `IDENTITY` columns, encryption, compression, indexes.

### Table Scope
- Standard tables — on disk, global, persistent.
- Temporary tables — `#` prefix, in TempDB, visible to creating scope + sub-scopes.
- Global temporary tables — `##` prefix, also visible to concurrent scopes.
- Table variables — defined with `DECLARE`, visible only to creating scope.
- Memory-Optimized tables — In-Memory OLTP, non-standard syntax.

### Create Table from Query (SELECT INTO)
```sql
SELECT <Expression List>
INTO <Table Name>
[FROM <Table Source>]
[WHERE <Filter>]
[GROUP BY <Grouping Expressions>...];
```
Only column names, order, and data types are created — no constraints, keys, indexes, identity, or defaults.

### TIMESTAMP / ROWVERSION
`TIMESTAMP` synonym for `ROWVERSION` deprecated since SQL Server 2008 R2. Neither is supported by AWS SCT (raises error `706`). Use a trigger to maintain.

### Syntax
```sql
CREATE TABLE [<Database Name>.<Schema Name>].<Table Name> (<Column Definitions>)
[ON{<Partition Scheme Name> (<Partition Column Name>)];
```

### Examples

Basic table:
```sql
CREATE TABLE MyTable
(
    Col1 INT NOT NULL PRIMARY KEY,
    Col2 VARCHAR(20) NOT NULL
);
```

Table with column constraints and identity:
```sql
CREATE TABLE MyTable
(
    Col1 INT NOT NULL PRIMARY KEY IDENTITY (1,1),
    Col2 VARCHAR(20) NOT NULL CHECK (Col2 <> ''),
    Col3 VARCHAR(100) NULL
    REFERENCES MyOtherTable (Col3)
);
```

Table with additional index:
```sql
CREATE TABLE MyTable
(
    Col1 INT NOT NULL PRIMARY KEY,
    Col2 VARCHAR(20) NOT NULL
    INDEX IDX_Col2 NONCLUSTERED
);
```

## MySQL

ANSI/ISO entry level conformity plus extensions. Unlike SQL Server (single set of physical files per database), Aurora MySQL creates separate files per table — File Groups don't apply.

### Aurora MySQL Extensions
`AUTO_INCREMENT`, encryption, compression, indexes.

### Table Scope
- Standard tables — on disk, global, persistent.
- Temporary tables — `CREATE TEMPORARY TABLE`, visible only to the creating session, dropped on session close.

### Create Table from Existing Table or Query
- `CREATE TABLE <New Table> LIKE <Source Table>` — empty table copying definition, attributes, and indexes.
- `CREATE TABLE … AS <Query Expression>` — similar to SQL Server `SELECT INTO`; can combine column definitions and query-derived columns.

```sql
CREATE TABLE NewTable
(
    Col1 INT
)
AS
SELECT Col1 AS Col2
FROM SourceTable;
```

### Converting TIMESTAMP / ROWVERSION
Aurora MySQL `TIMESTAMP` is a temporal type (NOT the SQL Server `ROWVERSION` synonym). Use a trigger to maintain a version number:

```sql
CREATE TABLE WorkItems
(
    WorkItemID INT AUTO_INCREMENT PRIMARY KEY,
    WorkItemDescription JSON NOT NULL,
    Status VARCHAR(10) NOT NULL DEFAULT 'Pending',
    VersionNumber INTEGER NULL
);

CREATE TRIGGER MaintainWorkItemVersionNumber
AFTER UPDATE
ON WorkItems FOR EACH ROW
SET NEW.VersionNumber = OLD.VersionNumber + 1;
```

### Syntax
```sql
CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <Table Name>
(<Create Definition> ,...)[<Table Options>];

<Column Definition>:
<Data Type> [NOT NULL | NULL]
[DEFAULT <Default Value>]
[AUTO_INCREMENT]
[UNIQUE [KEY]] [[PRIMARY] KEY]
[COMMENT <comment>]
```

### Examples

Basic table:
```sql
CREATE TABLE MyTable
(
    Col1 INT NOT NULL PRIMARY KEY,
    Col2 VARCHAR(20) NOT NULL
);
```

Table with auto-increment column:
```sql
CREATE TABLE MyTable
(
    Col1 INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Col2 VARCHAR(20) NOT NULL
    CHECK (Col2 <> ''),
    Col3 VARCHAR(100) NULL
    REFERENCES MyOtherTable (Col3)
);
```

Table with additional index:
```sql
CREATE TABLE MyTable
(
    Col1 INT NOT NULL PRIMARY KEY,
    Col2 VARCHAR(20) NOT NULL,
    INDEX IDX_Col2 (Col2)
);
```

## Conversion notes

| Feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| ANSI compliance | Entry level | Entry level | Basic syntax compatible. |
| Auto generated enumerator | `IDENTITY` | `AUTO_INCREMENT` | One per table. Insert NULL or 0 to generate. Must be indexed in Aurora MySQL. |
| Reseed auto value | `DBCC CHECKIDENT` | `ALTER TABLE` | |
| Index types | `CLUSTERED`, `NONCLUSTERED` | Implicit — PKs use clustered | |
| Physical storage location | `ON <File Group>` | Not supported | Managed by AWS. |
| Temporary tables | `#TempTable` | `CREATE TEMPORARY TABLE` | |
| Global temporary tables | `##GlobalTempTable` | Not supported | Use standard tables. |
| Table variables | `DECLARE @Table` | Not supported | |
| Create table as query | `SELECT… INTO` | `CREATE TABLE… AS` | |
| Copy table structure | Not supported | `CREATE TABLE… LIKE` | |
| Memory-optimized tables | Supported | Not supported | Consider Amazon ElastiCache (Redis). |

- `IDENTITY` columns must be rewritten to `AUTO_INCREMENT` (must be indexed).
- Unlike `SET IDENTITY_INSERT ON`, Aurora MySQL allows inserting explicit values directly.
- `SELECT INTO` → `CREATE TABLE … AS`.
- FKs in Aurora MySQL can point to non-unique parent values.
