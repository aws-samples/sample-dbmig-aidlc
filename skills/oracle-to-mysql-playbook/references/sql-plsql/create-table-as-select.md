# CREATE TABLE AS SELECT (CTAS)

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.ctas.html

**Conversion category:** Automatic (★★★★★ feature compatibility, ★★★★★ automation)
**SCT automation:** N/A

## Oracle

CTAS creates a new table from an existing table, copying column names, datatypes, and data. Populated from columns in the `SELECT` (or all columns with `SELECT *`). Filter with `WHERE`/`AND`; reshape with joins, `GROUP BY`, `ORDER BY`.

```sql
-- All columns
CREATE TABLE EMPS
AS
SELECT * FROM EMPLOYEES;

-- Select columns
CREATE TABLE EMPS
AS
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY FROM EMPLOYEES
ORDER BY 3 DESC;
```

## MySQL

MySQL conforms to ANSI/SQL CTAS and is compatible with Oracle. In MySQL these standard elements are optional:
* Parentheses around the `SELECT` (standard requires; MySQL doesn't).
* The `WITH [ NO ] DATA` clause (standard requires; MySQL doesn't).

```sql
-- All columns
CREATE TABLE EMPS AS SELECT * FROM EMPLOYEES;

-- Select columns
CREATE TABLE EMPS AS SELECT EMPLOYEE_ID, FIRST_NAME, SALARY FROM EMPLOYEES ORDER BY 3 DESC;
```

## Conversion notes
- Fully compatible — syntax is essentially identical; no changes typically required.
- AWS DMS can create the target table by selecting from source tables using CTAS.
