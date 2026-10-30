# Constraints (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.constraints.html

**Conversion category:** Automatic (Five-star compatibility, four-star automation)
**SCT automation:** High — SCT action code index: Constraints. Key differences: check constraints can't use subqueries. (The original playbook also said `SET DEFAULT` is missing. That is wrong: PostgreSQL supports `ON DELETE/UPDATE SET DEFAULT`, verified on 18.6.)

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): corrected the `SET DEFAULT` claim (verified supported), UNIQUE single-NULL semantics via `NULLS NOT DISTINCT` (verified), `NOCHECK` → `NOT VALID`/`NOT ENFORCED` (PG 18), named NOT NULL.

## SQL Server

Four constraint types: check, unique, primary key, foreign key.

Check constraint (Boolean; `UNKNOWN` is treated as `TRUE`, so the value is permitted):
```sql
CHECK (<Logical Expression>)
```

Unique constraint (only one NULL row allowed in SQL Server, unlike ANSI):
```sql
UNIQUE [CLUSTERED | NONCLUSTERED] (<Column List>)
```

Primary key (default index is clustered; all columns must be `NOT NULL`):
```sql
PRIMARY KEY [CLUSTERED | NONCLUSTERED] (<Column List>)
```

Foreign key (with Cascading Referential Integrity options: `NO ACTION`, `CASCADE`, `SET NULL`, `SET DEFAULT`):
```sql
FOREIGN KEY (<Referencing Column List>)
REFERENCES <Referenced Table>(<Referenced Column List>)
```

Examples:
```sql
-- Composite non-clustered primary key
CREATE TABLE MyTable
(
Col1 INT NOT NULL,
Col2 INT NOT NULL,
Col3 VARCHAR(20) NULL,
CONSTRAINT PK_MyTable
PRIMARY KEY NONCLUSTERED (Col1, Col2)
);

-- Table-level check constraint
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

-- Foreign key with multiple cascade actions
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

## PostgreSQL

Supported types: `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `CHECK`, `NOT NULL`, `EXCLUDE` (unique to PostgreSQL). Constraints on views aren't supported. PostgreSQL 18 adds temporal keys (`WITHOUT OVERLAPS` / `PERIOD`) and `NOT ENFORCED` CHECK/FK constraints.

Primary key (inline, named, out-of-line, alter, drop):
```sql
CREATE TABLE EMPLOYEES (
  EMPLOYEE_ID NUMERIC CONSTRAINT PK_EMP_ID PRIMARY KEY,
  FIRST_NAME VARCHAR(20),
  LAST_NAME VARCHAR(25),
  EMAIL VARCHAR(25));

ALTER TABLE SYSTEM_EVENTS
  ADD CONSTRAINT PK_EMP_ID PRIMARY KEY (EVENT_CODE, EVENT_TIME);

ALTER TABLE SYSTEM_EVENTS DROP CONSTRAINT PK_EMP_ID;
```

Foreign key — `ON DELETE` / `ON UPDATE` options: `CASCADE`, `RESTRICT`, `NO ACTION` (default). Difference between `RESTRICT` and `NO ACTION`: `NO ACTION` allows the check to be deferred to later in the transaction; `RESTRICT` doesn't.
```sql
CREATE TABLE EMPLOYEES (
  EMPLOYEE_ID NUMERIC PRIMARY KEY,
  FIRST_NAME VARCHAR(20),
  LAST_NAME VARCHAR(25),
  EMAIL VARCHAR(25),
  DEPARTMENT_ID NUMERIC,
  CONSTRAINT FK_FEP_ID
  FOREIGN KEY(DEPARTMENT_ID) REFERENCES DEPARTMENTS(DEPARTMENT_ID)
  ON DELETE CASCADE);

-- Add FK to existing table, validate separately
ALTER TABLE EMPLOYEES ADD CONSTRAINT FK_DEPT
  FOREIGN KEY (department_id)
  REFERENCES DEPARTMENTS (department_id) NOT VALID;
ALTER TABLE EMPLOYEES VALIDATE CONSTRAINT FK_DEPT;
```

Unique — **differs from SQL Server**. PostgreSQL by default accepts multiple NULLs, while SQL Server allows only one NULL per unique constraint. Use **`UNIQUE NULLS NOT DISTINCT`** (PG 15+) to get SQL Server's single-NULL behavior exactly (verified: the second NULL is rejected):
```sql
CREATE TABLE EMPLOYEES (
  EMPLOYEE_ID NUMERIC PRIMARY KEY,
  ...
  EMAIL VARCHAR(25) CONSTRAINT UNIQ_EMP_EMAIL UNIQUE NULLS NOT DISTINCT,   -- SQL Server semantics
  DEPARTMENT_ID NUMERIC);
```
SQL Server filtered unique indexes used to allow many NULLs (`CREATE UNIQUE INDEX … WHERE col IS NOT NULL`) map to PostgreSQL's default `UNIQUE`, or to a partial unique index.

Check (Boolean only — no subqueries; wrap subquery logic in a Boolean function returning TRUE/FALSE).

NOT NULL — PostgreSQL 18 records NOT NULL as a named constraint (`CONSTRAINT nn_email NOT NULL`), and it can be added `NOT VALID`. The older CHECK form also works:
```sql
CREATE TABLE EMPLOYEES (
  EMPLOYEE_ID NUMERIC PRIMARY KEY,
  FIRST_NAME VARCHAR(20) NOT NULL,
  LAST_NAME VARCHAR(25) NOT NULL,
  EMAIL VARCHAR(25) CONSTRAINT CHK_EMAIL
    CHECK(EMAIL IS NOT NULL));
```

SET CONSTRAINTS / deferral:
```sql
SET CONSTRAINTS { ALL | name [, ...] } { DEFERRED | IMMEDIATE }
```
- `DEFERRABLE` constraints can be deferred until commit; `NOT DEFERRABLE` always runs `IMMEDIATE`.
- `NOT VALID` (FK/check, and NOT NULL since PG 18) skips validation of existing rows; `VALIDATE CONSTRAINT` later scans the table to enforce it. This corresponds to SQL Server `ALTER TABLE … WITH NOCHECK ADD CONSTRAINT`.
- `NOT ENFORCED` (PG 18, CHECK/FK) keeps the constraint definition but does not check it, corresponding to SQL Server `ALTER TABLE … NOCHECK CONSTRAINT` (a disabled, "not trusted" constraint). `ALTER CONSTRAINT … ENFORCED` re-enables and validates it.

Create a PK/unique constraint from an existing index (constraint owns the index; dropping the constraint drops the index):
```sql
CREATE UNIQUE INDEX IDX_EMP_ID ON EMPLOYEES(EMPLOYEE_ID);
ALTER TABLE EMPLOYEES
  ADD CONSTRAINT PK_CON_UNIQ PRIMARY KEY USING INDEX IDX_EMP_ID;
```

## Conversion notes

Summary comparison:

| Feature | SQL Server | Aurora PostgreSQL |
|---|---|---|
| Check constraints | CHECK | CHECK |
| Unique constraints | UNIQUE | UNIQUE |
| Primary key constraints | PRIMARY KEY | PRIMARY KEY |
| Foreign key constraints | FOREIGN KEY | FOREIGN KEY |
| Cascaded referential actions | NO ACTION, CASCADE, SET NULL, SET DEFAULT | NO ACTION, CASCADE, SET NULL, **SET DEFAULT** (verified), RESTRICT; PG 15+ allows a column list for SET NULL / SET DEFAULT |
| UNIQUE and NULL | one NULL allowed | many NULLs by default; `NULLS NOT DISTINCT` = one NULL |
| Disabled constraints | `NOCHECK CONSTRAINT` | `NOT ENFORCED` (PG 18) |
| Untrusted (`WITH NOCHECK`) | yes | `NOT VALID` |
| Indexing of referencing columns | Not required | N/A |
| Indexing of referenced columns | PRIMARY KEY or UNIQUE | PRIMARY KEY or UNIQUE |

- `SET DEFAULT` referential action **is** available in PostgreSQL and converts directly (the original playbook was wrong). The column default must reference an existing parent row or the cascade fails.
- PostgreSQL check constraints cannot contain subqueries; SQL Server can use UDFs in check constraints to access other rows/tables. Replace with a Boolean function.
- PostgreSQL adds `RESTRICT` and the `EXCLUDE` constraint type not present in SQL Server.
- PostgreSQL supports `NOT VALID` / `VALIDATE CONSTRAINT` and `DEFERRABLE` constraint timing not available in SQL Server.
