# Case Sensitivity (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.casesensitivity.html

**Conversion category:** Assisted
**SCT automation:** AWS SCT lowercases object names by default; AWS DMS transformation rules can also lowercase schema/table/column names.

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
- AWS DMS transformation actions can change schema/table/column names to lowercase. See [Transformation rules and actions](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Transformations.html).
