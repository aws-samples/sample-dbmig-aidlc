# Oracle and MySQL Views

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.views.html

**Conversion category:** Automatic (four-star feature compatibility; four-star automation)
**SCT automation:** N/A

## Oracle

A view stores a named SQL query in the data dictionary with a predefined structure; it stores no data (virtual/logical table over one or more physical tables).

Privileges: `CREATE VIEW` (own schema), `CREATE ANY VIEW` (any schema); the owner needs `SELECT`/DML privileges on the source objects. `CREATE OR REPLACE` modifies a view without dropping it or losing granted privileges.

Common parameters: `CREATE OR REPLACE`, `FORCE` (create regardless of source existence/privileges), `VISIBLE`/`INVISIBLE` columns, `WITH READ ONLY` (disable DML), `WITH CHECK OPTION` (enforce DML constraints).

Simple view (single source, no aggregates; DML allowed):

```sql
CREATE OR REPLACE VIEW VW_EMP
AS
SELECT EMPLOYEE_ID, LAST_NAME, EMAIL, SALARY
FROM EMPLOYEES
WHERE DEPARTMENT_ID BETWEEN 100 AND 130;

UPDATE VW_EMP
SET EMAIL=EMAIL||'.org'
WHERE EMPLOYEE_ID=110;
-- 1 row updated.
```

Complex view (joins/aggregates/order by; DML not allowed directly — use `INSTEAD OF` triggers):

```sql
CREATE OR REPLACE VIEW VW_DEP
AS
SELECT B.DEPARTMENT_NAME, COUNT(A.EMPLOYEE_ID) AS CNT
FROM EMPLOYEES A JOIN DEPARTMENTS B USING(DEPARTMENT_ID)
GROUP BY B.DEPARTMENT_NAME;

UPDATE VW_DEP SET CNT=CNT +1 WHERE DEPARTMENT_NAME=90;
-- ORA-01732: data manipulation operation not legal on this view
```

## MySQL

Aurora MySQL views are also a `SELECT` over base tables/views, created with `CREATE VIEW`. The defining `SELECT` is evaluated when the view is created.

Restrictions:
- Cannot reference system or user-defined variables.
- Within a stored procedure/function, the `SELECT` cannot reference parameters or local variables.
- Cannot reference prepared-statement parameters.
- All referenced objects must exist at creation; dropping an underlying object causes an error on invocation.
- Cannot reference `TEMPORARY` tables; `TEMPORARY` views are not supported; views don't support triggers.
- Aliases limited to 64 characters (not 256).

Properties not in Oracle:
- `ALGORITHM` clause: `MERGE` (merge view definition into the outer query), `TEMPTABLE` (materialize internally), or `UNDEFINED`.
- `DEFINER` and `SQL SECURITY {DEFINER | INVOKER}` set the run-time permission context.

Updatable views: supported, with ANSI `WITH [LOCAL | CASCADED] CHECK OPTION` (default `CASCADED`). Generally only one-to-one source-to-exposed-row views are updatable; the following prevent updates: aggregate functions, `DISTINCT`, `GROUP BY`, `HAVING`, `UNION`/`UNION ALL`, subquery in the select list, certain joins, reference to a non-updatable view, `WHERE` subquery referencing a `FROM` table, `ALGORITHM = TEMPTABLE`, multiple references to a base-table column. `ORDER BY` is allowed but ignored if the outer query has its own `ORDER BY`.

Syntax:

```sql
CREATE [OR REPLACE]
  [ALGORITHM = {UNDEFINED | MERGE | TEMPTABLE}]
  [DEFINER = { <User> | CURRENT_USER }]
  [SQL SECURITY { DEFINER | INVOKER }]
  VIEW <View Name> [(<Column List>)]
  AS <SELECT Statement>
  [WITH [CASCADED | LOCAL] CHECK OPTION];
```

Example:

```sql
CREATE VIEW TotalSales
AS
SELECT Customer, SUM(TotalAmount) AS CustomerTotalAmount
GROUP BY Customer;

SELECT * FROM TotalSales ORDER BY CustomerTotalAmount DESC;
```

## Conversion notes

- Basic `CREATE [OR REPLACE] VIEW` converts directly; this is largely automatic.
- Oracle string concatenation `||` becomes `CONCAT()` in MySQL.
- Replace Oracle `INSTEAD OF` triggers on complex views — MySQL views don't support triggers; handle DML in the application or against base tables.
- `WITH CHECK OPTION` maps directly (add `LOCAL`/`CASCADED` scope).
- Watch the 64-character alias limit and the view restrictions (no variables, no TEMPORARY tables, objects must exist).
- Consider `ALGORITHM` (MERGE vs TEMPTABLE) and `SQL SECURITY` (DEFINER vs INVOKER) — Oracle has no direct equivalents.
