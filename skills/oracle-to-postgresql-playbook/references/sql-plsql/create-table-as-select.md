# CREATE TABLE AS SELECT (CTAS) Statement

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.ctas.html

**Conversion category:** Automatic (Five-star feature compatibility, five-star automation; no key differences)
**SCT automation:** Five-star automation level; SCT action code index N/A

## Oracle

CTAS creates a new table based on an existing table. It copies column names, data types, and data into a new table. The new table is populated from the columns named in the `SELECT`, or all columns with `SELECT *`. You can filter with `WHERE`/`AND`, and reshape using joins, `GROUP BY`, and `ORDER BY`.

```sql
-- All columns
CREATE TABLE EMPS
AS
SELECT * FROM EMPLOYEES;

-- Selected columns
CREATE TABLE EMPS
AS
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY FROM EMPLOYEES
ORDER BY 3 DESC;
```

## PostgreSQL

PostgreSQL conforms to the ANSI/SQL standard for CTAS and is compatible with Oracle's CTAS. Compared to the standard, PostgreSQL makes these optional:

- Parentheses around the `SELECT` (standard requires them; PG doesn't).
- The `WITH [ NO ] DATA` clause (standard requires it; PG doesn't).

Synopsis:

```sql
CREATE
[ [ GLOBAL | LOCAL ] { TEMPORARY | TEMP } | UNLOGGED ] TABLE [ IF NOT EXISTS ] table_name
[ (column_name [, ...] ) ]
[ WITH ( storage_parameter [= value] [, ... ] ) |
WITH OIDS | WITHOUT OIDS ]
[ ON COMMIT { PRESERVE ROWS | DELETE ROWS | DROP } ]
[ TABLESPACE tablespace_name ]
AS query
[ WITH [ NO ] DATA ]
```

Examples:

```sql
CREATE TABLE EMPS AS SELECT * FROM EMPLOYEES;

CREATE TABLE EMPS AS
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY FROM EMPLOYEES ORDER BY 3 DESC;

-- Structure only, no data
CREATE TABLE EMPS AS SELECT * FROM EMPLOYEES WITH NO DATA;
```

## Conversion notes

- Syntax is essentially identical; CTAS migrates with no rewrite.
- PostgreSQL adds `UNLOGGED`, `IF NOT EXISTS`, `ON COMMIT`, and `TABLESPACE` options.
- Use `WITH NO DATA` to copy structure only (Oracle uses `WHERE 1=0` or similar; PG has the explicit clause).
