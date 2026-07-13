# Table Constraints

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.constraints.html

**Conversion category:** Automatic (four-star feature compatibility, four-star automation)
**SCT automation:** Creating Tables action code index. PostgreSQL doesn't support `REF`, `ENABLE`/`DISABLE` keywords, or constraints on views.

## Oracle
Oracle offers six constraint types: **PRIMARY KEY**, **FOREIGN KEY**, **UNIQUE**, **CHECK**, **NOT NULL**, **REF**.

Constraints can be declared **inline** (part of column declaration) or **out-of-line** (separate clause in table DDL):

```sql
-- Inline
CREATE TABLE EMPLOYEES (EMP_ID NUMBER PRIMARY KEY,…);
-- Out-of-line
CREATE TABLE EMPLOYEES (EMP_ID NUMBER,…,
  CONSTRAINT PK_EMP_ID PRIMARY KEY(EMP_ID));
```
`NOT NULL` must be inline. Defined via `CREATE/ALTER TABLE` and `CREATE/ALTER VIEW` (views support only PK, FK, and unique). FK creation needs `REFERENCES` privilege on the parent table.

**PRIMARY KEY** — unique, not null, one per table; implicitly creates a unique index if none exists (system index dropped with the PK; a user index is not). Cannot be on `LOB`, `LONG`, `LONG RAW`, `VARRAY`, `NESTED TABLE`, `BFILE`, `REF`, `TIMESTAMP WITH TIME ZONE` (but `TIMESTAMP WITH LOCAL TIME ZONE` allowed). Composite PK limited to 32 columns.

```sql
CREATE TABLE EMPLOYEES (
  EMPLOYEE_ID NUMBER CONSTRAINT PK_EMP_ID PRIMARY KEY,
  FIRST_NAME VARCHAR2(20), LAST_NAME VARCHAR2(25), EMAIL VARCHAR2(25));

ALTER TABLE SYSTEM_EVENTS
  ADD CONSTRAINT PK_EMP_ID PRIMARY KEY (EVENT_CODE, EVENT_TIME);
```

**FOREIGN KEY** — child references parent PK/unique. Same datatype restrictions and 32-column limit. No `ON UPDATE` clause in Oracle. `ON DELETE CASCADE` and `ON DELETE NULL` supported. Referenced PK/unique must exist first; can't be created in a `CREATE TABLE` with subquery.

```sql
CREATE TABLE EMPLOYEES (
  EMPLOYEE_ID NUMBER PRIMARY KEY, ...,
  DEPARTMENT_ID NUMBER,
  CONSTRAINT FK_FEP_ID
  FOREIGN KEY(DEPARTMENT_ID) REFERENCES DEPARTMENTS(DEPARTMENT_ID)
  ON DELETE CASCADE);
```

**UNIQUE** — like PK but allows NULLs (multiple rows of NULLs OK if combination unique). Same datatype/column restrictions. Can't share columns with a PK.

```sql
EMAIL VARCHAR2(25) CONSTRAINT UNIQ_EMP_EMAIL UNIQUE,
```

**CHECK** — validate column values against a condition. Cannot reference other tables, non-deterministic functions (e.g. `CURRENT_DATE`), user-defined functions, or pseudo-columns (`CURRVAL`, `NEXTVAL`, `LEVEL`, `ROWNUM`).

```sql
EMAIL VARCHAR2(25)
  CHECK(REGEXP_LIKE (EMAIL, '^[A-Za-z]+@example.com?{1,3}$')),
```

**NOT NULL** — inline only.

**REF** — relationship between a `REF`-typed column and the object it references (scope/rowid/referential):

```sql
CREATE TYPE DEP_TYPE AS OBJECT (
  DEP_NAME VARCHAR2(60), DEP_ADDRESS VARCHAR2(300));
CREATE TABLE DEPARTMENTS_OBJ_T OF DEP_TYPE;
CREATE TABLE EMPLOYEES (
  EMP_NAME VARCHAR2(60), EMP_EMAIL VARCHAR2(60),
  EMP_DEPT REF DEPARTMENT_TYP REFERENCES DEPARTMENTS_OBJ_T);
```

**Special constraint states**: `DEFERRABLE`/`NOT DEFERRABLE`, `INITIALLY IMMEDIATE`/`INITIALLY DEFERRED`, `VALIDATE`/`NO VALIDATE`, `ENABLE`/`DISABLE` with `ENABLE VALIDATE`, `ENABLE NOVALIDATE`, `DISABLE VALIDATE`, `DISABLE NOVALIDATE`.

Use an existing index to enforce a PK/unique:
```sql
CREATE UNIQUE INDEX IDX_EMP_ID ON EMPLOYEES(EMPLOYEE_ID);
ALTER TABLE EMPLOYEES
  ADD CONSTRAINT PK_CON_UNIQ PRIMARY KEY(EMPLOYEE_ID) USING INDEX IDX_EMP_ID;
```

## PostgreSQL
Supported types: **PRIMARY KEY**, **FOREIGN KEY**, **UNIQUE**, **NOT NULL**, **EXCLUDE** (PostgreSQL-only). Oracle `REF` is **not supported**. Inline or out-of-line via `CREATE`/`ALTER TABLE`; views not supported. FK needs `REFERENCES` privilege.

**PRIMARY KEY** — ANSI SQL syntax, automatically creates a unique B-Tree index.

```sql
ALTER TABLE SYSTEM_EVENTS
  ADD CONSTRAINT PK_EMP_ID PRIMARY KEY (EVENT_CODE, EVENT_TIME);
ALTER TABLE SYSTEM_EVENTS DROP CONSTRAINT PK_EMP_ID;
```

**FOREIGN KEY** — same ANSI syntax. FK columns must have an explicit data type (Oracle doesn't require this). PostgreSQL supports both `ON DELETE` **and** `ON UPDATE` (Oracle has no `ON UPDATE`):
- `CASCADE`, `RESTRICT`, `NO ACTION` (default). Difference: `NO ACTION` allows the check to be deferred to later in the transaction; `RESTRICT` does not.

```sql
DEPARTMENT_ID NUMERIC REFERENCES DEPARTMENTS(DEPARTMENT_ID)   -- inline
CONSTRAINT FK_FEP_ID
  FOREIGN KEY(DEPARTMENT_ID) REFERENCES DEPARTMENTS(DEPARTMENT_ID)
  ON DELETE CASCADE
```

**UNIQUE** — auto-creates a B-Tree index; accepts multiple NULLs (like Oracle).

**CHECK** — must evaluate to Boolean:
```sql
EMAIL VARCHAR(25) CHECK(EMAIL ~ '(^[A-Za-z]+@example.com$)'),
```

**NOT NULL** — inline only; can name it when expressed as a CHECK:
```sql
EMAIL VARCHAR(25) CONSTRAINT CHK_EMAIL CHECK(EMAIL IS NOT NULL)
```

**Constraint states** via `SET CONSTRAINTS`: `DEFERRABLE`, `IMMEDIATE`, `NOT DEFERRABLE`.
```sql
SET CONSTRAINTS { ALL | name [, ...] } { DEFERRED | IMMEDIATE }
```
- `NOT VALID` (FK/CHECK only) — skip validating existing rows at creation.
- `VALIDATE CONSTRAINT` — scan the table and validate a previously `NOT VALID` constraint.
```sql
ALTER TABLE EMPLOYEES ADD CONSTRAINT FK_DEPT
  FOREIGN KEY (department_id)
  REFERENCES DEPARTMENTS (department_id) NOT VALID;
ALTER TABLE EMPLOYEES VALIDATE CONSTRAINT FK_DEPT;
```

Use an existing unique index for a PK/unique (index owned by the constraint and dropped with it):
```sql
CREATE UNIQUE INDEX IDX_EMP_ID ON EMPLOYEES(EMPLOYEE_ID);
ALTER TABLE EMPLOYEES
  ADD CONSTRAINT PK_CON_UNIQ PRIMARY KEY USING INDEX IDX_EMP_ID;
```

### Mapping summary
| Oracle | PostgreSQL |
|---|---|
| PRIMARY KEY / FOREIGN KEY / UNIQUE / CHECK / NOT NULL | Same |
| REF | Not supported |
| DEFERRABLE / NOT DEFERRABLE / SET CONSTRAINTS | Same |
| INITIALLY IMMEDIATE / INITIALLY DEFERRED | Same |
| ENABLE / ENABLE VALIDATE | Default; not a keyword |
| ENABLE NOVALIDATE | NOT VALID |
| DISABLE / DISABLE VALIDATE / DISABLE NOVALIDATE | DISABLE→use NOT VALID; VALIDATE/NOVALIDATE not supported |
| USING_INDEX_CLAUSE | table_constraint_using_index |
| View constraints | Not supported |
| Metadata: DBA_CONSTRAINTS | Metadata: PG_CONSTRAINT |

## Conversion notes
- PostgreSQL adds `ON UPDATE` (CASCADE/RESTRICT/NO ACTION) and an `EXCLUDE` constraint type not in Oracle.
- Oracle `REF` constraints and view constraints have no PostgreSQL equivalent — redesign required.
- `ENABLE`/`DISABLE` keywords don't exist in PostgreSQL; use `NOT VALID` + `VALIDATE CONSTRAINT` for deferred validation of new vs. existing data.
- FK columns must be explicitly typed in PostgreSQL.
- Both engines can build PK/unique constraints from a pre-existing index, but in PostgreSQL the index becomes owned by the constraint and is dropped with it.
