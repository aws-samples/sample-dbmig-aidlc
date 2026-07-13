# Virtual Columns

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.virtual.html

**Conversion category:** Automatic (four-star feature compatibility, five-star automation)
**SCT automation:** N/A (no action code index listed; high automation).

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
Before PostgreSQL 12 there was no direct equivalent. **PostgreSQL 12+ adds generated columns** (computed on the fly, or computed and stored) — similar to Oracle virtual columns.

Pre-12 workarounds:
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
  EXECUTE PROCEDURE FUNC_USER_FULL_NAME();

INSERT INTO EMPLOYEES (EMPLOYEE_ID, FIRST_NAME, LAST_NAME)
  VALUES(1, 'John', 'Smith'),(2, 'Steven', 'King');
-- FULL_NAME auto-populated: 'John Smith', 'Steven King'

CREATE INDEX IDX_USER_FULL_NAME ON EMPLOYEES(FULL_NAME);
```

## Conversion notes
- On Aurora PostgreSQL 12+, convert Oracle virtual columns to **generated columns** directly (closest match).
- Pre-12: use a view + SQL/PL-pgSQL function, or a `BEFORE INSERT/UPDATE` trigger to populate a stored column.
- Oracle function-based indexes on virtual columns map to PostgreSQL **expression indexes**.
- Note PostgreSQL function-as-column access uses `function_name(table_alias)` syntax with a row-type parameter.
