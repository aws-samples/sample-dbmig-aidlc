# Common Table Expressions (CTE)

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.cte.html

**Conversion category:** Automatic (Five-star feature compatibility, five-star automation; no key differences)
**SCT automation:** Five-star automation level; SCT action code index N/A

## Oracle

CTEs let you define a named subquery and reuse it multiple times within a query, reducing repetition and improving readability. Implemented with the `WITH` clause (ANSI SQL-99, in Oracle since 9.2). Behaves like an inline view or temporary table.

Syntax:

```sql
WITH <subquery name> AS (<subquery code>)[...]
SELECT <select list> FROM <subquery name>;
```

Example — employee count per department reused in the main query:

```sql
WITH DEPT_COUNT
(DEPARTMENT_ID, DEPT_COUNT) AS
(SELECT DEPARTMENT_ID, COUNT(*)
FROM EMPLOYEES
GROUP BY DEPARTMENT_ID)
SELECT E.FIRST_NAME ||' '|| E.LAST_NAME AS EMP_NAME,
D.DEPT_COUNT AS EMP_DEPT_COUNT
FROM EMPLOYEES E JOIN DEPT_COUNT D
USING (DEPARTMENT_ID)
ORDER BY 2;
```

## PostgreSQL

PostgreSQL conforms to ANSI SQL-99. CTEs work the same as Oracle as long as you avoid native Oracle elements (e.g., `CONNECT BY`).

Equivalent example:

```sql
WITH DEPT_COUNT
(DEPARTMENT_ID, DEPT_COUNT) AS (
SELECT DEPARTMENT_ID, COUNT(*) FROM EMPLOYEES GROUP BY DEPARTMENT_ID)
SELECT E.FIRST_NAME ||' '|| E.LAST_NAME AS EMP_NAME, D.DEPT_COUNT AS EMP_DEPT_COUNT
FROM EMPLOYEES E JOIN DEPT_COUNT D USING (DEPARTMENT_ID) ORDER BY 2;
```

PostgreSQL also supports the `RECURSIVE` modifier, letting a CTE reference its own result set:

```sql
WITH RECURSIVE t(n) AS (
VALUES (0)
UNION ALL
SELECT n+1 FROM t WHERE n < 5)
SELECT * FROM t;

 n
--
 0
 1
 2
 3
 4
 5
```

## Conversion notes

- Standard `WITH` CTEs migrate directly with no rewrite.
- Oracle hierarchical queries using `CONNECT BY` should be rewritten as `WITH RECURSIVE` in PostgreSQL.
- PostgreSQL's `WITH RECURSIVE` is the idiomatic replacement for Oracle recursive/hierarchical traversal.
