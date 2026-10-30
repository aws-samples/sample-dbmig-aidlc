# Common Table Expressions (CTE)

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.cte.html

**Conversion category:** Automatic (Five-star feature compatibility, five-star automation; no key differences)
**SCT automation:** Five-star automation level; SCT action code index N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): added the `CONNECT BY` → `WITH RECURSIVE … SEARCH/CYCLE` mapping (PG 14+, verified) and `MATERIALIZED`/`NOT MATERIALIZED` (PG 12+).

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

### CONNECT BY → WITH RECURSIVE … SEARCH / CYCLE (PG 14+, verified on 18.6)

```sql
-- Oracle
SELECT LPAD(' ', 2*(LEVEL-1)) || name, LEVEL, CONNECT_BY_ISCYCLE
FROM emp START WITH mgr IS NULL CONNECT BY NOCYCLE PRIOR id = mgr
ORDER SIBLINGS BY name;

-- PostgreSQL 18
WITH RECURSIVE t(id, mgr, name, lvl) AS (
  SELECT id, mgr, name, 1 FROM emp WHERE mgr IS NULL            -- START WITH
  UNION ALL
  SELECT e.id, e.mgr, e.name, t.lvl + 1 FROM emp e JOIN t ON e.mgr = t.id   -- CONNECT BY PRIOR id = mgr
) SEARCH DEPTH FIRST BY name SET ord                              -- ORDER SIBLINGS BY name
  CYCLE id SET is_cycle USING path                                 -- NOCYCLE / CONNECT_BY_ISCYCLE
SELECT repeat('  ', lvl - 1) || name, lvl, is_cycle FROM t ORDER BY ord;
```

| Oracle | PostgreSQL |
|---|---|
| `LEVEL` | a depth column incremented in the recursive term |
| `SYS_CONNECT_BY_PATH(name, '/')` | a text column: `'/' \|\| name` in the anchor, `t.path \|\| '/' \|\| e.name` in the recursive term |
| `CONNECT_BY_ROOT col` | carry the anchor's value down as a column |
| `CONNECT_BY_ISLEAF` | `NOT EXISTS (SELECT 1 FROM emp c WHERE c.mgr = t.id)` |
| `ORDER SIBLINGS BY x` | `SEARCH DEPTH FIRST BY x SET ord` … `ORDER BY ord` |
| `NOCYCLE`, `CONNECT_BY_ISCYCLE` | `CYCLE id SET is_cycle USING path` |
| Oracle recursive `WITH … SEARCH … SET`, `CYCLE … SET` (11gR2) | same clauses, nearly identical syntax |

### Planner behavior

Since PG 12, non-recursive CTEs referenced once are **inlined** (no longer an optimization fence). Use `WITH x AS MATERIALIZED (...)` to force one evaluation, like Oracle's `/*+ MATERIALIZE */` hint, or `NOT MATERIALIZED` to force inlining (both verified). Data-modifying CTEs (`WITH d AS (DELETE … RETURNING *) …`) are supported and have no Oracle counterpart.

## Conversion notes

- Standard `WITH` CTEs migrate directly with no rewrite.
- Oracle hierarchical queries using `CONNECT BY` should be rewritten as `WITH RECURSIVE` with `SEARCH`/`CYCLE` (PG 14+), using the mapping above.
- Oracle `/*+ MATERIALIZE */` / `/*+ INLINE */` hints on CTEs → `AS MATERIALIZED` / `AS NOT MATERIALIZED`.
- `UNION ALL` in the recursive term keeps duplicates like Oracle; `UNION` de-duplicates and can hide cycles.
