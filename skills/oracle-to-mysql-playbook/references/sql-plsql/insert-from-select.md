# INSERT FROM SELECT

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.ifs.html

**Conversion category:** Assisted (★★★★ feature compatibility, ★★★★ automation)
**SCT automation:** N/A — MySQL doesn't support `ERROR LOG` and subquery (DML_table_expression) options.

## Oracle

`INSERT FROM SELECT` inserts multiple rows from another table. Column order and datatypes must match between target and source.

```sql
-- Explicit columns
INSERT INTO EMPS (EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID)
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID
FROM EMPLOYEES WHERE SALARY > 10000;

-- Implicit
INSERT INTO EMPS
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID
FROM EMPLOYEES WHERE SALARY > 10000;

-- Subquery in DML_table_expression_clause
INSERT INTO
(SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID FROM EMPS)
VALUES (120, 'Kenny', 10000, 90);

-- error_logging_clause
ALTER TABLE EMPS ADD CONSTRAINT PK_EMP_ID PRIMARY KEY(employee_id);
EXECUTE DBMS_ERRLOG.CREATE_ERROR_LOG('EMPS', 'ERRLOG');
INSERT INTO EMPS
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID
FROM EMPLOYEES WHERE SALARY > 10000
LOG ERRORS INTO errlog ('Cannot Perform Insert') REJECT LIMIT 100;
```

## MySQL

Compatible with Oracle `INSERT FROM SELECT` except a few Oracle-specific features: the `conditional_insert_clause (ALL | FIRST | ELSE)`, the subquery-as-target form, and the `error_logging_clause`. Use `ON DUPLICATE KEY UPDATE` to handle duplicates.

```sql
-- Syntax
INSERT [LOW_PRIORITY | HIGH_PRIORITY] [IGNORE]
  [INTO] tbl_name
  [PARTITION (partition_name [, ...])]
  [(col_name [, ...])]
  SELECT ...
  [ON DUPLICATE KEY UPDATE assignment_list]

-- Explicit
INSERT INTO EMPS (EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID)
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID
FROM EMPLOYEES WHERE SALARY > 10000;

-- Implicit
INSERT INTO EMPS
SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID
FROM EMPLOYEES WHERE SALARY > 10000;

-- ON DUPLICATE KEY UPDATE replaces error_logging_clause use case
INSERT INTO EMPS
SELECT * from EMPLOYEES where EMPLOYEE_ID > 10
ON DUPLICATE KEY UPDATE
  EMPS.FIRST_NAME=EMPLOYEES.FIRST_NAME,
  EMPS.SALARY=EMPLOYEES.SALARY;
```

NOT compatible with MySQL:
```sql
INSERT INTO
(SELECT EMPLOYEE_ID, FIRST_NAME, SALARY, DEPARTMENT_ID FROM EMPS)
VALUES (120, 'Kenny', 10000, 90);
```

## Conversion notes
- Basic explicit/implicit `INSERT ... SELECT` migrates unchanged.
- Oracle subquery-as-insert-target is unsupported — rewrite as a plain `INSERT INTO table`.
- Replace Oracle `LOG ERRORS`/`DBMS_ERRLOG` error logging with `ON DUPLICATE KEY UPDATE` (or `INSERT IGNORE`) to handle constraint violations.
- Oracle multi-table `conditional_insert_clause` (`ALL`/`FIRST`/`ELSE`) is unsupported — rewrite as separate statements.
