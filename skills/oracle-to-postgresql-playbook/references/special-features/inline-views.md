# Inline Views

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.inlineviews.html

**Conversion category:** Automatic (Five-star feature compatibility, five-star automation)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): the FROM-subquery alias has been optional since PG 16 (verified), and the Oracle example's missing alias is called out.

## Oracle

An inline view is a `SELECT` statement in the `FROM` clause of another `SELECT`. It simplifies complex queries by condensing calculations/joins. Oracle allows **omitting the alias** for the inner (inline) query:
```sql
SELECT A.LAST_NAME, A.SALARY, A.DEPARTMENT_ID, B.SAL_AVG
FROM EMPLOYEES A,
(SELECT DEPARTMENT_ID, ROUND(AVG(SALARY))
AS SAL_AVG FROM EMPLOYEES GROUP BY DEPARTMENT_ID)
WHERE A.DEPARTMENT_ID = B.DEPARTMENT_ID;
```

## PostgreSQL

PostgreSQL calls these subselects/subqueries; functionality is identical. **Since PostgreSQL 16 the alias is optional** (verified on 18.6: `SELECT * FROM (SELECT 1)` works). PostgreSQL 15 and earlier raise `ERROR: subquery in FROM must have an alias`. Still add an alias whenever outer clauses reference the subquery's columns. The Oracle example above actually references `B.` without declaring it, so it needs the alias `B` on both engines:
```sql
SELECT A.LAST_NAME, A.SALARY, A.DEPARTMENT_ID, B.SAL_AVG
FROM EMPLOYEES A,
(SELECT DEPARTMENT_ID, ROUND(AVG(SALARY)) AS SAL_AVG
FROM EMPLOYEES GROUP BY DEPARTMENT_ID) B
WHERE A.DEPARTMENT_ID = B.DEPARTMENT_ID;
```

## Conversion notes
- On Aurora PostgreSQL 16+ (including 18), unaliased `FROM`-clause subqueries are accepted. Adding an alias is still the safe, portable convention, and it is required whenever the subquery's columns are referenced with a qualifier.
- Otherwise inline views convert automatically — fully compatible.
- Oracle old-style outer joins inside inline views (`(+)`) must be rewritten to ANSI `LEFT/RIGHT JOIN`. That conversion, not the alias, is the usual source of errors.
