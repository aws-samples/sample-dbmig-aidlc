# EXECUTE IMMEDIATE and PREPARE/EXECUTE

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.immediate.html

**Conversion category:** Assisted (★★★★ feature compatibility, ★★ automation)
**SCT automation:** Action code "EXECUTE IMMEDIATE" — use MySQL `PREPARE`; MySQL can't run SQL returning results with bind variables, nor anonymous blocks, via `EXECUTE`.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected EXECUTE IMMEDIATE … INTO (SELECT … INTO @var inside the prepared text works, verified); USING takes user variables only, one statement per PREPARE, no PREPARE in functions, backtick identifier quoting (QUOTE() is wrong for identifiers) — verified on both versions.

> **Security — dynamic SQL (mandatory, read before copying any example below):**
> SQL *values* must always be passed as bind variables (`:1` in Oracle, `?` in MySQL `PREPARE`) and
> never concatenated. SQL *identifiers* (table/column names) cannot be bound, so when a statement
> must be built dynamically you MUST map the input to a fixed **allowlist** of known-safe identifiers
> before it is placed into the statement text (MySQL has no `format()`/`%I` identifier-quoting
> helper). The Oracle example below concatenates a column name **only after validating it against the
> data dictionary** — that validation is a *required prerequisite*, not an optional safeguard. Never
> concatenate an unvalidated/user-supplied identifier into dynamic SQL.

## Oracle

`EXECUTE IMMEDIATE` parses and runs a dynamic SQL statement or anonymous PL/SQL block, with bind variable support.

```sql
-- Dynamic SQL with bind variables inside a procedure
CREATE OR REPLACE PROCEDURE raise_sal (col_val NUMBER, emp_col VARCHAR2, amount NUMBER) IS
  col_name VARCHAR2(30);
  sql_stmt VARCHAR2(350);
BEGIN
  SELECT COLUMN_NAME INTO col_name FROM USER_TAB_COLS
  WHERE TABLE_NAME = 'EMPLOYEES' AND COLUMN_NAME = emp_col;
  -- SECURITY: values are bound (:1, :2), but an identifier (the column name) cannot be bound and
  -- is concatenated. This is safe ONLY because col_name is validated against an allowlist first —
  -- the SELECT above returns a row only if emp_col is a real EMPLOYEES column, else NO_DATA_FOUND
  -- aborts. Never concatenate an unvalidated/user-supplied identifier into dynamic SQL.
  sql_stmt := 'UPDATE employees SET salary = salary + :1 WHERE ' || col_name || ' = :2';
  EXECUTE IMMEDIATE sql_stmt USING amount, col_val;
END raise_sal;
/

-- DDL
EXECUTE IMMEDIATE 'CREATE TABLE link_emp (idemp1 NUMBER, idemp2 NUMBER)';
EXECUTE IMMEDIATE 'ALTER SESSION SET SQL_TRACE TRUE';

-- Anonymous block with bind variables
EXECUTE IMMEDIATE 'BEGIN raise_sal (:col_val, :col_name, :amount); END;'
  USING 134, 'EMPLOYEE_ID', 10;
```

## MySQL

`PREPARE` parses a `SELECT`/`INSERT`/`UPDATE`/`DELETE`/`VALUES` statement under a name; `EXECUTE` runs it (with bind variables via `USING`). Statement names are not case-sensitive; re-preparing a name deallocates the previous one; scope is the session.

```sql
-- SELECT with bind variable (placeholder ?)
PREPARE stmt1 FROM 'SELECT count(*) FROM employees WHERE ID=?';
SET @man_id = 3;
EXECUTE stmt1 USING @man_id;

-- DML, no vars then with vars
PREPARE stmt1 FROM 'INSERT INTO numbers (a) VALUES (1)';
EXECUTE stmt1;
PREPARE stmt1 FROM 'INSERT INTO numbers (a) VALUES (?)';
SET @a = 3;
EXECUTE stmt1 USING @a;

-- DDL
PREPARE stmt1 FROM 'CREATE TABLE numbers (num integer)';
EXECUTE stmt1;
```

## Conversion notes

| Functionality | Oracle EXECUTE IMMEDIATE | MySQL PREPARE/EXECUTE |
|---|---|---|
| Run SQL returning results + bind vars | `EXECUTE IMMEDIATE 'select ... :1' INTO amount USING col_val;` | Put the `INTO` inside the prepared text with a user variable: `PREPARE s FROM 'SELECT COUNT(*) INTO @c FROM t WHERE id >= ?'; SET @id = p_id; EXECUTE s USING @id; SET amount = @c;` (verified). `EXECUTE … INTO` itself does not exist |
| Run DML with bind vars | `EXECUTE IMMEDIATE 'UPDATE ... :1 ... :2' USING amount, col_val;` | `PREPARE stmt FROM 'UPDATE ... ? ... ?'; EXECUTE stmt USING @amount,@col;` |
| Run DDL | `EXECUTE IMMEDIATE 'CREATE TABLE ...';` | `PREPARE stmt FROM 'CREATE TABLE ...'; EXECUTE stmt;` |
| Run anonymous block | `EXECUTE IMMEDIATE 'BEGIN ... END;';` | **N/A** — wrap logic in a stored procedure and `CALL` it |

- Bind placeholders change from Oracle `:1`/`:name` to MySQL `?` (positional), bound via `EXECUTE ... USING @var`.
- MySQL bind variables can only substitute data values — not identifiers (table/column names). Build identifier-dynamic SQL with `CONCAT` then `PREPARE`.
- No anonymous-block execution — refactor into stored procedures (a prepared `CALL p(...)` works, verified). Return single-row values with `SELECT … INTO @var` inside the prepared text.

Verified on Aurora MySQL 3.13 and 8.4.8:
- **`USING` accepts user variables only** (`@id`); `EXECUTE s USING p_id` with a routine parameter or local variable is a syntax error. Copy locals into `@` variables first. Those variables are session-global, so give them routine-specific names.
- A prepared statement holds **one** statement; `'SELECT 1; SELECT 2'` fails.
- `PREPARE` is allowed in procedures but **not in functions or triggers** (error 1336); Oracle functions that use `EXECUTE IMMEDIATE` must become procedures.
- **Identifiers:** quote with backticks and double embedded backticks — `CONCAT('SELECT … FROM `', REPLACE(p_tab, '`', '``'), '`')` (verified). `QUOTE()` produces a **string literal**, not an identifier, so it is wrong for table names. Validate identifiers against `information_schema` when they come from callers.
- `DEALLOCATE PREPARE s` after use; prepared statements are per session and count against `max_prepared_stmt_count` (16382, verified).
- `EXECUTE IMMEDIATE … RETURNING INTO` and `BULK COLLECT INTO` have no equivalent.
