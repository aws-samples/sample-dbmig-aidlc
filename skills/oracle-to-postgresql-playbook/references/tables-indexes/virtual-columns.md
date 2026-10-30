# Virtual Columns

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.virtual.html

**Conversion category:** Automatic (four-star feature compatibility, five-star automation)
**SCT automation:** N/A (no action code index listed; high automation).

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): PG 18 `VIRTUAL` generated columns (default) with a verified VIRTUAL-vs-STORED capability matrix (no index/unique/FK/UDF on virtual), DML/load restrictions, `SET EXPRESSION`.

## Oracle
Virtual columns appear as normal columns but their values are **calculated, not stored**. Rules:
- Can't be based on other virtual columns; can only reference columns of the same table.
- Data type may be specified explicitly or derived from the expression.
- Usable with constraints, indexes, partitioning, and foreign keys.
- Functions in the expression must be deterministic at table-creation time.
- Can't be manipulated by DML; can be used in `WHERE` and as part of DML commands.
- Creating an index on a virtual column creates a **function-based index**.
- Not supported with index-organized, external, object, cluster, or temporary tables.
- Expression output must be a scalar value.
- `GENERATED ALWAYS AS` and `VIRTUAL` keywords are optional (clarity only).

```sql
COLUMN_NAME [datatype] [GENERATED ALWAYS] AS (expression) [VIRTUAL]
```

```sql
CREATE TABLE EMPLOYEES (
  EMPLOYEE_ID NUMBER,
  FIRST_NAME VARCHAR2(20),
  LAST_NAME VARCHAR2(25),
  USER_NAME VARCHAR2(25),
  EMAIL AS (LOWER(USER_NAME) || '@example.com'),
  HIRE_DATE DATE,
  BASE_SALARY NUMBER,
  SALES_COUNT NUMBER,
  FINAL_SALARY NUMBER GENERATED ALWAYS AS
    (CASE WHEN SALES_COUNT >= 10 THEN BASE_SALARY +
    (BASE_SALARY * (SALES_COUNT * 0.05)) END)
  VIRTUAL);

INSERT INTO EMPLOYEES
  (EMPLOYEE_ID, FIRST_NAME, LAST_NAME, USER_NAME, HIRE_DATE, BASE_SALARY, SALES_COUNT)
  VALUES(1, 'John', 'Smith', 'jsmith', '17-JUN-2003', 5000, 21);

SELECT email FROM EMPLOYEES;   -- jsmith@example.com, FINAL_SALARY 10250
```

## PostgreSQL
Before PostgreSQL 12 there was no direct equivalent. PostgreSQL 12 added **stored** generated columns, and **PostgreSQL 18 adds `VIRTUAL` generated columns and makes `VIRTUAL` the default**. They are computed on read, which is the same model as Oracle virtual columns.

```sql
-- Aurora PostgreSQL 18 (verified on 18.6)
CREATE TABLE employees (
  employee_id  numeric PRIMARY KEY,
  user_name    varchar(25),
  base_salary  numeric,
  sales_count  numeric,
  email        text    GENERATED ALWAYS AS (lower(user_name) || '@example.com'),          -- VIRTUAL (default)
  final_salary numeric GENERATED ALWAYS AS (CASE WHEN sales_count >= 10
                 THEN base_salary + base_salary * sales_count * 0.05 END) STORED          -- STORED: indexable
);
-- INSERT … (1, 'JSmith', 5000, 21) → email = 'jsmith@example.com', final_salary = 10250.00
```

**VIRTUAL vs STORED on PG 18 (all verified on 18.6):**

| Oracle virtual column used with… | PG 18 `VIRTUAL` | PG 18 `STORED` |
|---|---|---|
| plain `SELECT` / `WHERE` | yes | yes |
| `CHECK` / `NOT NULL` constraint | yes | yes |
| index (function-based index) | **no** (`indexes on virtual generated columns are not supported`) | yes |
| `UNIQUE` / `PRIMARY KEY` / referenced by FK | **no** | yes |
| partition key | **no** (neither kind; partition by the expression instead: `PARTITION BY RANGE ((lower(user_name)))`) | no |
| user-defined function in the expression | **no** (`generation expression uses user-defined function`) | yes (function must be `IMMUTABLE`) |
| storage cost / write cost | none | stored on every write |
| `ALTER TABLE … ADD COLUMN` | instant | rewrites the table |

**Rule of thumb:** convert to `VIRTUAL` (the default) unless the Oracle column is indexed, unique, referenced by a foreign key, or uses a user-defined function, in which case use `STORED`. Alternatively, keep it `VIRTUAL` and create an **expression index on the expression itself** (`CREATE INDEX ON employees ((lower(user_name) || '@example.com'))`), which the planner uses for queries written against the expression.

Like Oracle, generated columns cannot be written by DML (`cannot insert a non-DEFAULT value`, verified). Inserts must omit them or use `DEFAULT`, and AWS DMS / `COPY` loads must exclude them from the column list.

Pre-12 workarounds (legacy, for reference):
- **Views** — include the function in the view definition.
- **Function as a column** — a function takes table row values and returns the derived value; can also back an **expression index** (≈ Oracle function-based index).

```sql
CREATE TABLE EMPLOYEES (
  EMPLOYEE_ID NUMERIC PRIMARY KEY,
  FIRST_NAME VARCHAR(20),
  LAST_NAME VARCHAR(25),
  USER_NAME VARCHAR(25));

CREATE OR REPLACE FUNCTION USER_EMAIL(EMPLOYEES)
  RETURNS text AS $$
  SELECT (LOWER($1.USER_NAME) || '@example.com')
  $$ STABLE LANGUAGE SQL;

INSERT INTO EMPLOYEES (EMPLOYEE_ID, FIRST_NAME, LAST_NAME, USER_NAME)
  VALUES(1, 'John', 'Smith', 'jsmith'), (2, 'Steven', 'King', 'sking');

SELECT EMPLOYEE_ID, FIRST_NAME, LAST_NAME, USER_NAME, USER_EMAIL(EMPLOYEES)
  FROM EMPLOYEES;
-- 1 John Smith jsmith jsmith@example.com
-- 2 Steven King sking sking@example.com

CREATE VIEW employees_function AS
SELECT EMPLOYEE_ID, FIRST_NAME, LAST_NAME, USER_NAME, USER_EMAIL(EMPLOYEES)
  FROM EMPLOYEES;

CREATE INDEX IDX_USER_EMAIL ON EMPLOYEES(USER_EMAIL(EMPLOYEES));
```

Expression index used by the planner:
```sql
SET enable_seqscan = OFF;
EXPLAIN SELECT * FROM EMPLOYEES WHERE USER_EMAIL(EMPLOYEES) = 'jsmith@example.com';
-- Index Scan using idx_user_email on employees
--   Index Cond: ((lower((user_name)::text) || '@example.com'::text) = 'jsmith@example.com'::text)
```

### DML support via trigger (populate a real column automatically)
```sql
CREATE TABLE EMPLOYEES (
  EMPLOYEE_ID NUMERIC PRIMARY KEY,
  FIRST_NAME VARCHAR(20), LAST_NAME VARCHAR(25), FULL_NAME VARCHAR(25));

CREATE OR REPLACE FUNCTION FUNC_USER_FULL_NAME ()
  RETURNS trigger as '
    BEGIN
    NEW.FULL_NAME = NEW.FIRST_NAME || '' '' || NEW.LAST_NAME;
    RETURN NEW;
    END;
' LANGUAGE plpgsql;

CREATE TRIGGER TRG_USER_FULL_NAME BEFORE INSERT OR UPDATE
  ON EMPLOYEES FOR EACH ROW
  EXECUTE FUNCTION FUNC_USER_FULL_NAME();

INSERT INTO EMPLOYEES (EMPLOYEE_ID, FIRST_NAME, LAST_NAME)
  VALUES(1, 'John', 'Smith'),(2, 'Steven', 'King');
-- FULL_NAME auto-populated: 'John Smith', 'Steven King'

CREATE INDEX IDX_USER_FULL_NAME ON EMPLOYEES(FULL_NAME);
```

## Conversion notes
- On Aurora PostgreSQL 18, convert Oracle virtual columns to **`GENERATED ALWAYS AS (…)` columns**: `VIRTUAL` by default, `STORED` when they are indexed, unique, FK targets or use user-defined functions (table above).
- Every function in the expression must be `IMMUTABLE` (Oracle's "deterministic" requirement). `to_char(date, …)` and timezone-dependent casts are not.
- `ALTER TABLE … ALTER COLUMN … SET EXPRESSION AS (…)` (PG 17+) changes the expression. On PG 18 it is refused for virtual columns in tables that have CHECK constraints (verified), so drop and re-add the column in that case.
- Pre-12 workarounds (view + function, or `BEFORE INSERT/UPDATE` trigger) are obsolete on Aurora PostgreSQL 18; use them only when the expression needs a non-immutable function.
- Oracle function-based indexes on virtual columns map to PostgreSQL **expression indexes**.
- Note PostgreSQL function-as-column access uses `function_name(table_alias)` syntax with a row-type parameter.
