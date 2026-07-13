# EXECUTE IMMEDIATE and PostgreSQL EXECUTE / PREPARE

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.immediate.html

**Conversion category:** Assisted (Four-star feature compatibility, two-star automation)
**SCT automation:** Two-star automation level; SCT action code index N/A

> **Security — dynamic SQL (mandatory, read before copying any example below):**
> SQL *values* must always be passed as bind variables (`:1` in Oracle, `$1` in PostgreSQL) and
> never concatenated. SQL *identifiers* (table/column names) cannot be bound, so when a statement
> must be built dynamically you MUST do one of:
> 1. map the input to a fixed **allowlist** of known-safe identifiers, or
> 2. quote it with PostgreSQL `format()` and the `%I` placeholder (identifier-safe quoting).
>
> The Oracle example below concatenates a column name **only after validating it against the data
> dictionary** — that validation is a *required prerequisite*, not an optional safeguard. Do not copy
> the concatenation without it. In converted PostgreSQL code, prefer `format('… %I …', ident)` over
> concatenation in every case.

## Oracle

`EXECUTE IMMEDIATE` parses and runs a dynamic SQL statement or anonymous PL/SQL block at runtime, with bind variables.

```sql
CREATE OR REPLACE PROCEDURE raise_sal (col_val NUMBER, emp_col VARCHAR2, amount NUMBER) IS
  col_name VARCHAR2(30);
  sql_stmt VARCHAR2(350);
BEGIN
  -- validate column name
  SELECT COLUMN_NAME INTO col_name FROM USER_TAB_COLS
  WHERE TABLE_NAME = 'EMPLOYEES' AND COLUMN_NAME = emp_col;

  -- SECURITY: values are bound (:1, :2), but an identifier (the column name) cannot be bound and
  -- is concatenated. This is safe ONLY because col_name is validated against an allowlist first —
  -- the SELECT above returns a row only if emp_col is a real EMPLOYEES column, else NO_DATA_FOUND
  -- aborts. Never concatenate an unvalidated/user-supplied identifier into dynamic SQL.
  -- dynamic statement with bind variables
  sql_stmt := 'UPDATE employees SET salary = salary + :1 WHERE ' || col_name || ' = :2';

  EXECUTE IMMEDIATE sql_stmt USING amount, col_val;
END raise_sal;
/

-- DDL via EXECUTE IMMEDIATE
EXECUTE IMMEDIATE 'CREATE TABLE link_emp (idemp1 NUMBER, idemp2 NUMBER)';
EXECUTE IMMEDIATE 'ALTER SESSION SET SQL_TRACE TRUE';

-- Anonymous block with bind variables
EXECUTE IMMEDIATE 'BEGIN raise_sal (:col_val, :col_name, :amount); END;'
  USING 134, 'EMPLOYEE_ID', 10;
```

## PostgreSQL

PostgreSQL `EXECUTE` (in PL/pgSQL) prepares and runs commands dynamically, including DDL and result retrieval, with bind variables via `USING`. Use `format()` with `%I`/`%s` for dynamic identifiers/values.

```sql
-- SELECT with dynamic table name + bind variable
DO $$DECLARE
  Tabname varchar(30) := 'employees';
  num integer := 1;
  cnt integer;
BEGIN
  EXECUTE format('SELECT count(*) FROM %I WHERE manager = $1', tabname)
  INTO cnt USING num;
  RAISE NOTICE 'Count is % int table %', cnt, tabname;
END$$;

-- DML with/without variables
DO $$DECLARE
BEGIN
  EXECUTE 'INSERT INTO numbers (a) VALUES (1)';
  EXECUTE format('INSERT INTO numbers (a) VALUES (%s)', 42);
END$$;

-- DDL
DO $$DECLARE
BEGIN
  EXECUTE 'CREATE TABLE numbers (num integer)';
END$$;
```

> `%s` formats the argument as a simple string (NULL → empty string). `%I` treats it as an SQL identifier (double-quoted if needed); NULL is an error.

### PREPARE (reusable prepared statements)

`PREPARE` parses a `SELECT`/`INSERT`/`UPDATE`/`DELETE`/`VALUES` once under a name so later `EXECUTE` calls skip re-parsing. Valid for the current session; DDL on referenced objects forces a hard re-parse on next `EXECUTE`.

```sql
PREPARE numplan (int, text, bool) AS
INSERT INTO numbers VALUES($1, $2, $3);

EXECUTE numplan(100, 'New number 100', 't');
EXECUTE numplan(101, 'New number 101', 't');
EXECUTE numplan(102, 'New number 102', 'f');
```

## Summary

| Functionality | Oracle EXECUTE IMMEDIATE | PostgreSQL EXECUTE |
|---|---|---|
| SQL w/ results + binds | `EXECUTE IMMEDIATE 'select salary from employees WHERE ' \|\| col_name \|\| ' = :1' INTO amount USING col_val;` | `EXECUTE format('select salary from employees WHERE %I = $1', col_name) INTO amount USING col_val;` |
| DML w/ binds | `EXECUTE IMMEDIATE 'UPDATE employees SET salary = salary + :1 WHERE ' \|\| col_name \|\| ' = :2' USING amount, col_val;` | `EXECUTE format('UPDATE employees SET salary = salary + $1 WHERE %I = $2', col_name) USING amount, col_val;` |
| DDL | `EXECUTE IMMEDIATE 'CREATE TABLE link_emp (idemp1 NUMBER, idemp2 NUMBER)';` | `EXECUTE 'CREATE TABLE link_emp (idemp1 integer, idemp2 integer)';` |
| Anonymous block | `EXECUTE IMMEDIATE 'BEGIN DBMS_OUTPUT.PUT_LINE("Anonymous Block"); END;';` | `DO $$DECLARE BEGIN ... END$$;` |

## Conversion notes

- `EXECUTE IMMEDIATE` → PL/pgSQL `EXECUTE`. String concatenation of identifiers **must** become `format('… %I …', ident)` (with the identifier validated against an allowlist where it originates from input) to be safe and correct — never concatenate a raw identifier.
- Bind placeholders change from `:1`, `:2` to `$1`, `$2`, still passed via `USING`.
- Dynamic anonymous blocks (`EXECUTE IMMEDIATE 'BEGIN … END;'`) become a `DO $$ … $$;` block.
- For repeated execution, prefer `PREPARE`/`EXECUTE` for performance.
- Use `%I` for identifiers and `%L` for quoted literals to prevent SQL injection.
