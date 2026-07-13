# Case Sensitivity Differences

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.case.html

**Conversion category:** Assisted
**SCT automation:** AWS SCT defaults object names to lower-case for PostgreSQL; use AWS DMS transformations to change schema/table/column names to lower case.

## Oracle
Oracle object names are **not** case sensitive. Names are stored/resolved in upper-case by default unless quoted.

## PostgreSQL
PostgreSQL object names **are** case sensitive. By default, PostgreSQL folds unquoted names to **lower-case**. To preserve upper-case or mixed-case names, you must wrap the name in double quotes.

Create a table named `EMPLOYEES` (upper-case) — requires double quotes:

```sql
CREATE TABLE "EMPLOYEES" (
  EMP_ID NUMERIC PRIMARY KEY,
  EMP_FULL_NAME VARCHAR(60) NOT NULL,
  AVG_SALARY NUMERIC NOT NULL);
```

Create a table named `employees` (lower-case) — no quotes:

```sql
CREATE TABLE EMPLOYEES (
  EMP_ID NUMERIC PRIMARY KEY,
  EMP_FULL_NAME VARCHAR(60) NOT NULL,
  AVG_SALARY NUMERIC NOT NULL);
```

## Conversion notes
- If you don't use double quotes, PostgreSQL looks for object names in their lower-case form.
- For `CREATE` commands without double quotes, PostgreSQL creates objects with lower-case names.
- To create, query, or manipulate an upper-cased (or mixed) object name, you must use double quotes consistently everywhere the name is referenced.
- Recommended approach: standardize on lower-case names via AWS DMS transformations to avoid the need to quote names throughout application code.
