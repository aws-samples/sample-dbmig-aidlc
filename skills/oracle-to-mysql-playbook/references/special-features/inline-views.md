# Oracle and MySQL Inline Views

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.inlineviews.html

**Conversion category:** Automatic (five-star feature compatibility; five-star automation)
**SCT automation:** N/A — fully compatible; only mandatory aliases differ.

## Oracle

Inline views are `SELECT` statements placed in the `FROM` clause of another `SELECT`. They simplify complex queries by condensing calculations/joins. The inner statement does **not** require an alias in Oracle.

```sql
SELECT A.LAST_NAME, A.SALARY, A.DEPARTMENT_ID, B.SAL_AVG
FROM EMPLOYEES A,
(SELECT DEPARTMENT_ID, ROUND(AVG(SALARY))
 AS SAL_AVG FROM EMPLOYEES GROUP BY DEPARTMENT_ID)
WHERE A.DEPARTMENT_ID = B.DEPARTMENT_ID;
```

## MySQL

MySQL refers to inline views as sub-selects or subqueries; functionality is the same. Running the Oracle example as-is fails with: `SQL Error[1248][4200]: Every derived table must have its own alias`, because MySQL **requires** an alias on the derived table. Mandatory aliases are the only major difference.

```sql
SELECT A.LAST_NAME, A.SALARY, A.DEPARTMENT_ID, B.SAL_AVG
FROM EMPLOYEES A,
(SELECT DEPARTMENT_ID, ROUND(AVG(SALARY)) AS SAL_AVG
 FROM EMPLOYEES GROUP BY DEPARTMENT_ID) B
WHERE A.DEPARTMENT_ID = B.DEPARTMENT_ID;
```

## Conversion notes

- Add a mandatory alias (e.g., `B`) to every derived table / inline view in the `FROM` clause.
- No other changes are typically needed; this conversion is essentially automatic.
