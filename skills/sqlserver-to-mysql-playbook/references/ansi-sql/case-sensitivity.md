# Case Sensitivity Differences for ANSI SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.casesensitivity.html

**Conversion category:** Assisted
**SCT automation:** N/A (use AWS DMS transformations to change names to lowercase)

In SQL Server, object name case sensitivity is determined by the collation. In Aurora
MySQL, names are case sensitive and controlled by the `lower_case_table_names` parameter.

Recommended `lower_case_table_names` values:
- **0** — names stored as given, comparisons are case-sensitive. Valid for all RDS for MySQL versions.
- **1** — names stored in lowercase, comparisons are not case-sensitive. Valid for RDS for MySQL 5.6, 5.7, and 8.0.19+.

Operational notes:
- Aurora MySQL 2.10+: reboot all reader instances after changing `lower_case_table_names` and rebooting the writer.
- Aurora MySQL 3: the value is set permanently at cluster creation time. Set up a custom parameter group before upgrading.
- With an Aurora global database, you can't do an in-place upgrade from v2 to v3 if `lower_case_table_names` is turned on.
- Don't change `lower_case_table_names` for existing instances — it can cause inconsistencies with PITR backups and read replicas.
- Read replicas must use the same value as the source.
- Column, index, stored routine, event names, and column aliases are NOT case sensitive on either platform.

## SQL Server

Object name case sensitivity is governed by the collation.

```sql
CREATE TABLE EMPLOYEES (
    EMP_ID NUMERIC PRIMARY KEY,
    EMP_FULL_NAME VARCHAR(60) NOT NULL,
    AVG_SALARY NUMERIC NOT NULL);
```

## MySQL

By default, object names are stored in lowercase. MySQL looks for object names with the exact case as written in the query (when `lower_case_table_names = 0`).

Create a table named EMPLOYEES in uppercase:

```sql
CREATE TABLE EMPLOYEES (
    EMP_ID NUMERIC PRIMARY KEY,
    EMP_FULL_NAME VARCHAR(60) NOT NULL,
    AVG_SALARY NUMERIC NOT NULL);
```

Create a table named employees in lowercase:

```sql
CREATE TABLE employees (
    EMP_ID NUMERIC PRIMARY KEY,
    EMP_FULL_NAME VARCHAR(60) NOT NULL,
    AVG_SALARY NUMERIC NOT NULL);
```

Turn off table name case sensitivity by setting `lower_case_table_names = 1`.

## Conversion notes
- SQL Server case sensitivity = collation; Aurora MySQL case sensitivity = `lower_case_table_names`.
- In most cases, use AWS DMS transformations to convert schema, table, and column names to lowercase.
- Column, index, stored routine, event names, and column aliases are case-insensitive on both platforms.
- See [Identifier Case Sensitivity](https://dev.mysql.com/doc/refman/5.7/en/identifier-case-sensitivity.html) in the MySQL documentation.
