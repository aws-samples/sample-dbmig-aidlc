# INSERT FROM SELECT Statement

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.ifs.html

**Conversion category:** Assisted (Four-star feature compatibility, four-star automation; minor rewrites for Oracle-only clauses)
**SCT automation:** Four-star automation level; SCT action code index N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): `LOG ERRORS` alternatives beyond `ON CONFLICT`, `INSERT ALL` via data-modifying CTEs (verified), `RETURNING`.

## Oracle

`INSERT FROM SELECT` inserts multiple rows into a table from another table. Column ordering and data types must match between target and source.

```sql
-- Explicit column list
INSERT INTO EMPS (EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID)
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID
FROM EMPLOYEES
WHERE SALARY > 10000;

-- Implicit column list
INSERT INTO EMPS
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID
FROM EMPLOYEES
WHERE SALARY > 10000;

-- Subquery in DML_table_expression_clause (Oracle-only)
INSERT INTO
(SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID FROM EMPS)
VALUES (120, 'Kenny', 10000, 90);
```

Oracle error logging with `error_logging_clause`:

```sql
ALTER TABLE EMPS ADD CONSTRAINT PK_EMP_ID PRIMARY KEY(employee_id);
EXECUTE DBMS_ERRLOG.CREATE_ERROR_LOG('EMPS', 'ERRLOG');
INSERT INTO EMPS
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID
FROM EMPLOYEES
WHERE SALARY > 10000
LOG ERRORS INTO errlog ('Cannot Perform Insert') REJECT LIMIT 100;
```
Invalid records are redirected to the `ERRLOG` table rather than failing the insert.

## PostgreSQL

PostgreSQL `INSERT FROM SELECT` is mostly compatible with Oracle, except:
- No `conditional_insert_clause` (`ALL | FIRST | ELSE`).
- No `error_logging_clause`. Use the `ON CONFLICT` clause instead to capture/handle errors.

Syntax:

```sql
[ WITH [ RECURSIVE ] with_query [, ...] ]
INSERT INTO table_name [ AS alias ] [ ( column_name [, ...] ) ]
[ OVERRIDING { SYSTEM | USER} VALUE ]
{ DEFAULT VALUES | VALUES ( { expression | DEFAULT } [, ...] ) [, ...] | query }
[ ON CONFLICT [ conflict_target ] conflict_action ]
[ RETURNING * | output_expression [ [ AS ] output_name ] [, ...] ]

-- conflict_target:
( { index_column_name | ( index_expression ) } [ COLLATE collation ] [ opclass ] [, ...] ) [ WHERE index_predicate ]
ON CONSTRAINT constraint_name

-- conflict_action:
DO NOTHING
DO UPDATE SET { column_name = { expression | DEFAULT } |
  ( column_name [, ...] ) = [ ROW ]( { expression | DEFAULT } [, ...] ) |
  ( column_name [, ...] ) = ( sub-SELECT ) } [, ...]
  [ WHERE condition ]
```

Note: `OVERRIDING` (PG 10+) is relevant for identity columns. `SYSTEM VALUE` only applies to `GENERATED ALWAYS` identity columns; otherwise it is ignored.

Examples:

```sql
-- Explicit
INSERT INTO EMPS (EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID)
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID
FROM EMPLOYEES WHERE SALARY > 10000;

-- Implicit
INSERT INTO EMPS
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID
FROM EMPLOYEES WHERE SALARY > 10000;

-- ON CONFLICT to handle unique violations (error-logging alternative)
ALTER TABLE EMPS ADD CONSTRAINT PK_EMP_ID PRIMARY KEY(employee_id);
INSERT INTO EMPS
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID
FROM EMPLOYEES WHERE SALARY > 10000
ON CONFLICT on constraint PK_EMP_ID DO NOTHING;
```

The `INSERT INTO (SELECT ...) VALUES (...)` subquery form is NOT supported in PostgreSQL.

## Conversion notes

- Basic explicit/implicit `INSERT … SELECT` migrates directly.
- Rewrite Oracle's `LOG ERRORS INTO … REJECT LIMIT` (and `DBMS_ERRLOG`) using `ON CONFLICT … DO NOTHING` / `DO UPDATE`. That only covers **unique/exclusion violations**. For other row errors (check, FK, type conversion), either pre-filter the source with the same predicates, or loop over rows in PL/pgSQL with a `BEGIN … EXCEPTION WHEN others THEN INSERT INTO errlog … END` block per row. The per-row block is slow because each one is a subtransaction, so use it only for small or exceptional batches. For file loads, PG 17/18 `COPY … (ON_ERROR ignore, REJECT_LIMIT n)` covers type-conversion errors.
- The `INSERT INTO (subquery) VALUES (...)` form must be rewritten as a normal `INSERT INTO table VALUES`.
- Oracle multi-table conditional inserts (`INSERT ALL`/`FIRST`) have no direct PG equivalent. Use **data-modifying CTEs** so the source is read once in one statement (verified):
  ```sql
  WITH src AS (SELECT * FROM staging),
       a   AS (INSERT INTO t_small SELECT * FROM src WHERE amount <= 1000 RETURNING 1)
  INSERT INTO t_large SELECT * FROM src WHERE amount > 1000;
  ```
  For `INSERT FIRST`, make the `WHERE` conditions mutually exclusive (`NOT` of the earlier conditions).
- `RETURNING` on `INSERT … SELECT` replaces Oracle `RETURNING … BULK COLLECT INTO`.
