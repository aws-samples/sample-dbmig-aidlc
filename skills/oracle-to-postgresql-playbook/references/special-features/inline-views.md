# Inline Views

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.inlineviews.html

**Conversion category:** Automatic (Five-star feature compatibility, five-star automation)
**SCT automation:** N/A

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

PostgreSQL calls these subselects/subqueries; functionality is identical. However, **aliases are mandatory** for the subquery in `FROM`. Running the Oracle example as-is raises: `ERROR: subquery in FROM must have an alias`. Add an alias (e.g. `B`):
```sql
SELECT A.LAST_NAME, A.SALARY, A.DEPARTMENT_ID, B.SAL_AVG
FROM EMPLOYEES A,
(SELECT DEPARTMENT_ID, ROUND(AVG(SALARY)) AS SAL_AVG
FROM EMPLOYEES GROUP BY DEPARTMENT_ID) B
WHERE A.DEPARTMENT_ID = B.DEPARTMENT_ID;
```

## Conversion notes
- The only meaningful difference: **PostgreSQL requires an alias** for every `FROM`-clause subquery; Oracle allows omitting it.
- Otherwise inline views convert automatically — fully compatible.
