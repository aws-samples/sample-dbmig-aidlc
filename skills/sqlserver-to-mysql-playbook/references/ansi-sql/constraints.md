# Constraints for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.constraints.html

**Conversion category:** Assisted (Four star feature compatibility)
**SCT automation:** Four star automation level

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): CHECK is enforced on 3 / 8.4 (corrected); verified multiple-NULL unique keys and a single-NULL workaround, 8.4 FK-to-unique rule, ON DELETE SET DEFAULT silently acting as RESTRICT, NOT ENFORCED for NOCHECK.

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

Aurora MySQL 3 and 8.4 support all ANSI constraint types **including `CHECK`**, which is enforced since MySQL 8.0.16 (verified, error 3819). Constraint names (symbols) are optional; auto-generated if omitted. (The original "CHECK is parsed but ignored" describes MySQL 5.7.)

### Unique Constraints
Aurora MySQL provides unique indexes (no separate unique constraint object). It **permits multiple rows with NULL** (verified) — SQL Server allows only one NULL per unique constraint. To keep SQL Server semantics, put the unique key on a stored generated column that maps NULL to a sentinel (`ux INT AS (IFNULL(u, -2147483648)) STORED, UNIQUE (ux)` — the second NULL then fails with 1062, verified), or a functional key part. A single-column INT unique index can be referenced via the `_rowid` alias.

### Primary Key Constraints
A PK is a unique index where all columns are NOT NULL. Always named `PRIMARY` and always clustered (cannot be NON CLUSTERED). Keep PKs short — every secondary index stores a copy of the clustering key. Single-column INTEGER PK can be referenced via `_rowid`.

### Foreign Key Constraints
- Not supported for partitioned tables.
- On Aurora MySQL 3, FKs may reference NON-unique columns in the parent (leading columns of an index). **Aurora MySQL 8.4 blocks this** (`restrict_fk_on_non_standard_key` = ON, error 6125, verified); reference a PRIMARY or UNIQUE key, as SQL Server requires anyway.
- Referential actions: `RESTRICT`, `CASCADE`, `SET NULL`, `NO ACTION`. Default is `RESTRICT`. `NO ACTION` is synonymous with `RESTRICT` (always validated immediately).
- `SET DEFAULT` is NOT supported by InnoDB — and it is a **silent trap**: `ON DELETE SET DEFAULT` is accepted and shown by `SHOW CREATE TABLE`, but deleting a referenced parent row fails with error 1451 as if `RESTRICT` (verified on 3.13 and 8.4). Convert to a `BEFORE DELETE` trigger on the parent that updates children, or application logic.
- Self-referencing `ON UPDATE CASCADE`/`SET NULL` recursions are treated as RESTRICT to prevent infinite loops. Cascades limited to 15 levels deep.

### Check Constraints
Enforced on Aurora MySQL 3 / 8.4 (MySQL 8.0.16+). `CHECK … NOT ENFORCED` and `ALTER TABLE … ALTER CHECK c [NOT] ENFORCED` replace SQL Server `WITH NOCHECK` / `NOCHECK CONSTRAINT` (verified: `information_schema.table_constraints.ENFORCED` = `NO`). Restrictions: no subqueries, no stored functions, no non-deterministic functions (`NOW()`), and no reference to an `AUTO_INCREMENT` column. SQL Server CHECK constraints calling UDFs need a trigger instead.

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
| Check constraints | `CHECK` | `CHECK` (enforced, 8.0.16+) | No UDFs/subqueries/`NOW()` in the expression. |
| Unique constraints | `UNIQUE` | `UNIQUE` | |
| Primary key constraints | `PRIMARY KEY` | `PRIMARY KEY` | |
| Foreign key constraints | `FOREIGN KEY` | `FOREIGN KEY` | |
| Cascaded referential actions | `NO ACTION`, `CASCADE`, `SET NULL`, `SET DEFAULT` | `RESTRICT`, `CASCADE`, `SET NULL`, `NO ACTION` | `NO ACTION` and `RESTRICT` are synonymous. |
| Indexing of referencing columns | Not required | Required | Index created silently if not specified. |
| Indexing of referenced columns | `PRIMARY KEY` or `UNIQUE` | Required | 3.x accepts a non-unique index; 8.4 requires PRIMARY/UNIQUE (verified). |
| Unique with NULLs | one NULL allowed | many NULLs allowed | generated-column workaround above |
| Cascade recursion | Not allowed, discovered at `CREATE` time | Not allowed, discovered at run time | |

- Aurora MySQL doesn't support `SET DEFAULT` (accepted but acts as `RESTRICT` — verified).
- Convert SQL Server `CHECK` constraints directly; use triggers only for CHECKs that call UDFs or query other tables. Avoid `ENUM`/`SET` as CHECK replacements — they change the column type and sort order.
- Partitioned tables cannot have FKs (error 1506, verified).
- Constraint names are optional in Aurora MySQL, mandatory in SQL Server table constraints.
