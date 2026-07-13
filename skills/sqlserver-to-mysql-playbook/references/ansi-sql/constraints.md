# Constraints for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.constraints.html

**Conversion category:** Assisted (Four star feature compatibility)
**SCT automation:** Four star automation level

**Key differences:** Unsupported `CHECK`. Indexing requirements for `UNIQUE`.

## SQL Server

Four types of constraints: check, unique, primary key, foreign key.

### Check Constraints
```sql
CHECK (<Logical Expression>)
```
Boolean expressions evaluating to TRUE, FALSE, or UNKNOWN. For check constraints, UNKNOWN is treated as TRUE (value permitted). In SQL Server, user-defined functions can be used in constraints to access other rows/tables/databases (not allowed by ANSI SQL).

### Unique Constraints
```sql
UNIQUE [CLUSTERED | NONCLUSTERED] (<Column List>)
```
SQL Server allows a NULL value in only one row (ANSI allows multiple). Default index type is non-clustered. Backed by a unique index for efficiency.

### Primary Key Constraints
```sql
PRIMARY KEY [CLUSTERED | NONCLUSTERED] (<Column List>)
```
All PK columns must be NOT NULL. One PK per table. Default index type is clustered.

### Foreign Key Constraints
```sql
FOREIGN KEY (<Referencing Column List>)
REFERENCES <Referenced Table>(<Referenced Column List>)
```
Referenced columns must be PRIMARY KEY or UNIQUE. Referencing columns are not auto-indexed. Cascading referential integrity (CRI) options: `NO ACTION`, `CASCADE`, `SET NULL`, `SET DEFAULT`.

### Examples

Composite non-clustered primary key:
```sql
CREATE TABLE MyTable
(
    Col1 INT NOT NULL,
    Col2 INT NOT NULL,
    Col3 VARCHAR(20) NULL,
    CONSTRAINT PK_MyTable
    PRIMARY KEY NONCLUSTERED (Col1, Col2)
);
```

Table-level check constraint:
```sql
CREATE TABLE MyTable
(
    Col1 INT NOT NULL,
    Col2 INT NOT NULL,
    Col3 VARCHAR(20) NULL,
    CONSTRAINT PK_MyTable
    PRIMARY KEY NONCLUSTERED (Col1, Col2),
    CONSTRAINT CK_MyTableCol1Col2
    CHECK (Col2 >= Col1)
);
```

Foreign key with cascade actions:
```sql
CREATE TABLE MyChildTable
(
    Col1 INT NOT NULL PRIMARY KEY,
    Col2 INT NOT NULL,
    Col3 INT NOT NULL,
    CONSTRAINT FK_MyChildTable_MyParentTable
        FOREIGN KEY (Col2, Col3)
        REFERENCES MyParentTable (Col1, Col2)
        ON DELETE NO ACTION
        ON UPDATE CASCADE
);
```

## MySQL

Aurora MySQL supports all ANSI constraint types except CHECK. Constraint names (symbols) are optional; auto-generated if omitted. CHECK syntax is parsed but ignored.

### Unique Constraints
Aurora MySQL provides unique indexes (no separate unique constraint object). Permits multiple rows with NULL values. A single-column INT unique index can be referenced via the `_rowid` alias.

### Primary Key Constraints
A PK is a unique index where all columns are NOT NULL. Always named `PRIMARY` and always clustered (cannot be NON CLUSTERED). Keep PKs short — every secondary index stores a copy of the clustering key. Single-column INTEGER PK can be referenced via `_rowid`.

### Foreign Key Constraints
- Not supported for partitioned tables.
- Contrary to ANSI standard, FKs may reference NON-unique columns in the parent (columns must be leading columns of an index).
- Referential actions: `RESTRICT`, `CASCADE`, `SET NULL`, `NO ACTION`. Default is `RESTRICT`. `NO ACTION` is synonymous with `RESTRICT` (always validated immediately).
- `SET DEFAULT` is NOT supported (InnoDB engine).
- Self-referencing `ON UPDATE CASCADE`/`SET NULL` recursions are treated as RESTRICT to prevent infinite loops. Cascades limited to 15 levels deep.

### Check Constraints
Parsed without syntax errors but ignored and not stored. Workarounds: triggers, stored routines, or `ENUM`/`SET` types for value lists.

### Syntax
```sql
CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <Table Name>
(
    <Column Definition>
    [CONSTRAINT [<Symbol>]]
        PRIMARY KEY (<Column List>)
    | [CONSTRAINT [<Symbol>]]
        UNIQUE [INDEX|KEY] [<Index Name>] [<Index Type>] (<Column List>)
    | [CONSTRAINT [<Symbol>]]
        FOREIGN KEY [<Index Name>] (<Column List>)
            REFERENCES <Table Name> (<Column List>)
                [ON DELETE RESTRICT | CASCADE | SET NULL | NO ACTION | SET DEFAULT]
                [ON UPDATE RESTRICT | CASCADE | SET NULL | NO ACTION | SET DEFAULT]
);
```

### Examples

Composite primary key:
```sql
CREATE TABLE MyTable
(
    Col1 INT NOT NULL,
    Col2 INT NOT NULL,
    Col3 VARCHAR(20) NULL,
    CONSTRAINT PRIMARY KEY (Col1, Col2)
);
```

Named foreign key with cascade actions:
```sql
CREATE TABLE MyChildTable
(
    Col1 INT NOT NULL PRIMARY KEY,
    Col2 INT NOT NULL,
    Col3 INT NOT NULL,
    FOREIGN KEY (Col2, Col3)
    REFERENCES MyParentTable (Col1, Col2)
    ON DELETE NO ACTION
    ON UPDATE CASCADE
);
```

## Conversion notes

| Feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Check constraints | `CHECK` | Not supported | Aurora MySQL parses `CHECK` syntax but ignores it. |
| Unique constraints | `UNIQUE` | `UNIQUE` | |
| Primary key constraints | `PRIMARY KEY` | `PRIMARY KEY` | |
| Foreign key constraints | `FOREIGN KEY` | `FOREIGN KEY` | |
| Cascaded referential actions | `NO ACTION`, `CASCADE`, `SET NULL`, `SET DEFAULT` | `RESTRICT`, `CASCADE`, `SET NULL`, `NO ACTION` | `NO ACTION` and `RESTRICT` are synonymous. |
| Indexing of referencing columns | Not required | Required | Index created silently if not specified. |
| Indexing of referenced columns | `PRIMARY KEY` or `UNIQUE` | Required | Aurora MySQL doesn't enforce uniqueness of referenced columns. |
| Cascade recursion | Not allowed, discovered at `CREATE` time | Not allowed, discovered at run time | |

- Aurora MySQL doesn't support `SET DEFAULT` (InnoDB only).
- Use triggers/stored routines for complex CHECK logic; use `ENUM`/`SET` for value-list CHECKs.
- Constraint names are optional in Aurora MySQL, mandatory in SQL Server table constraints.
