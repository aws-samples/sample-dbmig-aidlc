# Case Sensitivity (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.casesensitivity.html

**Conversion category:** Assisted
**SCT automation:** AWS SCT lowercases object names by default; AWS DMS transformation rules can also lowercase schema/table/column names.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): 63-byte identifier truncation, case-insensitive data comparison via ICU nondeterministic collations (PG 18 `LIKE` support, verified) / `citext`.

## SQL Server

By default SQL Server object names are case insensitive. A case sensitive database can be created by changing the `COLLATION` property.

## PostgreSQL

PostgreSQL object names are case insensitive and folded to lowercase unless double-quoted. By default AWS SCT uses lowercase names for PostgreSQL.

Create a table forced to uppercase (must be double-quoted to create, query, or manage):

```sql
CREATE TABLE "EMPLOYEES" (
  EMP_ID NUMERIC PRIMARY KEY,
  EMP_FULL_NAME VARCHAR(60) NOT NULL,
  AVG_SALARY NUMERIC NOT NULL);
```

Create a table in lowercase (no quotes — PostgreSQL folds to lowercase):

```sql
CREATE TABLE EMPLOYEES (
  EMP_ID NUMERIC PRIMARY KEY,
  EMP_FULL_NAME VARCHAR(60) NOT NULL,
  AVG_SALARY NUMERIC NOT NULL);
```

## Conversion notes
- If source code has objects with identical names in different case, keep unique names in the converted code — enclose in double quotation marks or rename manually.
- Without double quotes, PostgreSQL creates objects with lowercase names. To use uppercase/mixed case names, you must double-quote them everywhere (create, query, manage).
- **Identifier length:** PostgreSQL truncates identifiers to **63 bytes** silently (verified on 18.6). SQL Server allows 128 characters, so check long table, column, constraint and index names during assessment and choose unique short names.
- **Data comparisons**, a bigger issue than object names: SQL Server's default collations (`SQL_Latin1_General_CP1_CI_AS`) are **case-insensitive**, and PostgreSQL's default is case-sensitive. On Aurora PostgreSQL 18, use a **nondeterministic ICU collation**, which now also supports `LIKE` (PG 18, verified), or `citext` for columns that must compare case-insensitively. See `../tsql/collations.md`.
- AWS DMS transformation actions can change schema/table/column names to lowercase. See [Transformation rules and actions](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Transformations.html).
