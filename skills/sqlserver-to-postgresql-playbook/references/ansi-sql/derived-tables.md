# Derived Tables (ANSI SQL)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.sql.derivedtables.html

**Conversion category:** Automatic (Five-star compatibility, five-star automation)
**SCT automation:** N/A. No key differences.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): confirmed compatible; PG 16 optional alias.

## SQL Server

Derived tables (ANSI SQL:2011) are like CTEs, but the referenced query appears inside the `FROM` clause. They enable more complex join queries.

Example:
```sql
SELECT name, salary, average_salary
FROM (SELECT AVG(salary)
  FROM employee) AS workers (average_salary), employee
WHERE salary > average_salary
ORDER BY salary DESC;
```

## PostgreSQL

PostgreSQL implements derived tables and is fully compatible with SQL Server derived tables.

Example (identical):
```sql
SELECT name, salary, average_salary
FROM (SELECT AVG(salary)
  FROM employee) AS workers (average_salary), employee
WHERE salary > average_salary
ORDER BY salary DESC;
```

## Conversion notes
- Fully compatible — no rewrite required.
- Since PostgreSQL 16 the derived-table alias is optional (verified on 18.6). SQL Server requires it, so converted code always has one anyway.
- Column alias lists on the derived table (`AS workers (average_salary)`) work the same in both engines.
