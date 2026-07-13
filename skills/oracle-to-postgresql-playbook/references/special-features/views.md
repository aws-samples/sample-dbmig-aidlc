# Views

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.views.html

**Conversion category:** Assisted (Four-star feature compatibility, four-star automation)
**SCT automation:** SCT action code index: Views.

## Oracle

A view stores a named SQL query in the data dictionary; it holds no data (a virtual/logical table over one or more physical tables).

Privileges: `CREATE VIEW` (own schema), `CREATE ANY VIEW` (any schema); owner needs `SELECT`/`DML` privileges on source objects.

Common parameters:
- `CREATE OR REPLACE` — recreate existing or create new (keeps granted privileges).
- `FORCE` — create regardless of source object existence/privileges.
- `VISIBLE`/`INVISIBLE` — column visibility.
- `WITH READ ONLY` — disable DML.
- `WITH CHECK OPTION` — enforcement level for DML on the view.

**Simple view** (single source table, no aggregates) — DML allowed, affects base table:
```sql
CREATE OR REPLACE VIEW VW_EMP
AS
SELECT EMPLOYEE_ID, LAST_NAME, EMAIL, SALARY
FROM EMPLOYEES
WHERE DEPARTMENT_ID BETWEEN 100 AND 130;

UPDATE VW_EMP
SET EMAIL=EMAIL||'.org'
WHERE EMPLOYEE_ID=110;
```

**Complex view** (joins/aggregates/order by) — no direct DML (use `INSTEAD OF` triggers):
```sql
CREATE OR REPLACE VIEW VW_DEP
AS
SELECT B.DEPARTMENT_NAME, COUNT(A.EMPLOYEE_ID) AS CNT
FROM EMPLOYEES A JOIN DEPARTMENTS B USING(DEPARTMENT_ID)
GROUP BY B.DEPARTMENT_NAME;

UPDATE VW_DEP SET CNT=CNT +1 WHERE DEPARTMENT_NAME=90;
-- ORA-01732: data manipulation operation not legal on this view
```

## PostgreSQL

PostgreSQL views are similar — a stored query over base tables, run on each access.

Synopsis:
```sql
CREATE [ OR REPLACE ] [ TEMP | TEMPORARY ] [ RECURSIVE ] VIEW name [ (
column_name [, ...] ) ]
[ WITH ( view_option_name [= view_option_value] [, ... ] ) ]
AS query
[ WITH [ CASCADED | LOCAL ] CHECK OPTION ]
```

- Privileges: role/user needs `SELECT` and `DML` on base objects to create a view.
- `CREATE [OR REPLACE] VIEW` — like Oracle, but a re-created view must keep the same column structure (names, order, types); otherwise drop first:
  ```sql
  CREATE [OR REPLACE] VIEW VW_NAME AS SELECT COLUMNS FROM TABLE(s) [WHERE CONDITIONS];
  DROP VIEW [IF EXISTS] VW_NAME;
  ```
- `WITH [ CASCADED | LOCAL ] CHECK OPTION` — verify `INSERT`/`UPDATE` against the view condition; `LOCAL` checks only this view, `CASCADED` checks all underlying views hierarchically.
- **DML on views:** simple views are **automatically updatable** (no `INSTEAD OF` trigger required, unlike Oracle complex views). A view can mix updatable and read-only columns; a column is updatable if it references an updatable base-table column.
- Views with `INSTEAD INSERT` triggers can be used with `COPY`: `COPY view FROM source;`
- PG 13+: rename view columns with `ALTER VIEW [ IF EXISTS ] name RENAME [ COLUMN ] column_name TO new_column_name` (before 13, had to use `ALTER TABLE`).

Examples:
```sql
-- no CHECK OPTION
CREATE OR REPLACE VIEW VW_DEP AS
SELECT DEPARTMENT_ID, DEPARTMENT_NAME, MANAGER_ID, LOCATION_ID FROM DEPARTMENTS
WHERE LOCATION_ID=1700;
UPDATE VW_DEP SET LOCATION_ID=1600;   -- 21 rows updated

-- with LOCAL CHECK OPTION
CREATE OR REPLACE VIEW VW_DEP AS
SELECT DEPARTMENT_ID, DEPARTMENT_NAME, MANAGER_ID, LOCATION_ID FROM DEPARTMENTS
WHERE LOCATION_ID=1700 WITH LOCAL CHECK OPTION;
UPDATE VW_DEP SET LOCATION_ID=1600;
-- ERROR: new row violates check option for view "vw_dep"
```

## Conversion notes
- Highly compatible — `CREATE OR REPLACE VIEW` and `WITH CHECK OPTION` map closely.
- Key difference: PostgreSQL **simple views are automatically updatable**, whereas Oracle requires `INSTEAD OF` triggers for DML on complex views. PostgreSQL complex views still need `INSTEAD OF` triggers for DML.
- Re-creating a view in PostgreSQL requires identical column structure; otherwise `DROP VIEW` first.
- Oracle `FORCE`, `VISIBLE/INVISIBLE` column options have no direct PostgreSQL equivalent.
- View column rename requires PG 13+ for `ALTER VIEW ... RENAME COLUMN`.
