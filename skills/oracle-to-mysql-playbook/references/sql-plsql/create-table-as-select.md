# CREATE TABLE AS SELECT (CTAS)

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.ctas.html

**Conversion category:** Automatic (★★★★★ feature compatibility, ★★★★★ automation)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): WITH [NO] DATA is a syntax error (corrected); CTAS copies no keys/indexes, CREATE TABLE … LIKE, derived types, inline PRIMARY KEY — verified on both versions.

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
* The `WITH [ NO ] DATA` clause — **not accepted at all**: `… WITH NO DATA` is a syntax error (verified on 3.13 and 8.4). Use `WHERE 1 = 0` or `CREATE TABLE … LIKE`.

```sql
-- All columns
CREATE TABLE EMPS AS SELECT * FROM EMPLOYEES;

-- Select columns
CREATE TABLE EMPS AS SELECT EMPLOYEE_ID, FIRST_NAME, SALARY FROM EMPLOYEES ORDER BY 3 DESC;
```

## Conversion notes
- Mostly compatible; changes to make (verified on Aurora MySQL 3.13 and 8.4.8):
  - CTAS copies column names and types only — **no primary key, indexes or constraints** (no index rows for the CTAS table in `information_schema.statistics`). Declare them inline: `CREATE TABLE t (PRIMARY KEY (id)) AS SELECT …`, or add them afterwards.
  - `CREATE TABLE new LIKE old` copies the structure **with** indexes but no data or FKs; follow with `INSERT … SELECT`.
  - Expression columns get derived types (`LENGTH(e)` → `int`, `NOW()` → `datetime`); cast expressions to the intended type in the select list.
  - Oracle `NOLOGGING`, `PARALLEL`, `TABLESPACE`, `COMPRESS` clauses → remove.
  - Since MySQL 8.0.21, CTAS is atomic and allowed with GTID-based replication.
  - CTAS commits implicitly (it is DDL).
- AWS DMS can create the target table by selecting from source tables using CTAS.
