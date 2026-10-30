# CREATE TABLE AS SELECT (CTAS) Statement

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.ctas.html

**Conversion category:** Automatic (Five-star feature compatibility, five-star automation; no key differences)
**SCT automation:** Five-star automation level; SCT action code index N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): removed `WITH OIDS` (gone since PG 12, verified), `LIKE … INCLUDING ALL`, `UNLOGGED` caveats on Aurora.

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
[ { TEMPORARY | TEMP } | UNLOGGED ] TABLE [ IF NOT EXISTS ] table_name
[ (column_name [, ...] ) ]
[ USING method ]
[ WITH ( storage_parameter [= value] [, ... ] ) | WITHOUT OIDS ]
[ ON COMMIT { PRESERVE ROWS | DELETE ROWS | DROP } ]
[ TABLESPACE tablespace_name ]
AS query
[ WITH [ NO ] DATA ]
-- WITH OIDS was removed in PG 12 (syntax error on 18.6); GLOBAL/LOCAL are accepted but ignored.
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
- Like Oracle, CTAS copies column names, types and data, but **not** constraints, defaults, indexes or identity. To copy the definition, use `CREATE TABLE new (LIKE src INCLUDING ALL);` (verified), then `INSERT … SELECT`.
- Oracle `CTAS … NOLOGGING` / `PARALLEL` → PostgreSQL `UNLOGGED` (verified) is faster but **not crash-safe**: it is emptied after a crash and its data is not visible on Aurora Replicas. Use it only for scratch/staging tables, then `ALTER TABLE … SET LOGGED`. CTAS itself can use parallel query for the `SELECT` part.
