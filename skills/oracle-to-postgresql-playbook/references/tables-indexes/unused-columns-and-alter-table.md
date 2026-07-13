# Unused Columns and ALTER TABLE

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.alter.html

**Conversion category:** Manual (two-star feature compatibility)
**SCT automation:** No automation. N/A. PostgreSQL doesn't support unused columns.

## Oracle
Oracle can mark columns as **unused** — not physically dropped but treated as dropped and not restorable. `SELECT` doesn't retrieve them and `DESCRIBE` doesn't show them. The advantage is avoiding the high load of physically dropping a column from a large table: mark it unused now, drop it physically later.

```sql
ALTER TABLE EMPLOYEES SET UNUSED (COMMISSION_PCT);
ALTER TABLE EMPLOYEES SET UNUSED (JOB_ID, COMMISSION_PCT);

SELECT * FROM USER_UNUSED_COL_TABS;
-- TABLE_NAME  COUNT
-- EMPLOYEES   3

ALTER TABLE EMPLOYEES DROP UNUSED COLUMNS;   -- physically drop
```

## PostgreSQL
No "unused" column concept. But `ALTER TABLE ... DROP COLUMN` is already fast: it doesn't physically remove the column, only makes it invisible to SQL. On-disk size isn't reduced immediately — the space is reclaimed gradually by new DML, or forcibly via `VACUUM FULL` (or an `ALTER TABLE` that forces a rewrite).

```sql
ALTER TABLE EMPLOYEES DROP COLUMN COMMISSION_PCT;

SELECT TABLE_NAME, COLUMN_NAME
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_NAME = 'emps1' AND COLUMN_NAME=LOWER('COMMISSION_PCT');
-- (0 rows)

VACUUM FULL EMPLOYEES;
VACUUM FULL VERBOSE EMPLOYEES;   -- with activity report
```

## Conversion notes
- The Oracle two-step (`SET UNUSED` then `DROP UNUSED COLUMNS`) maps to PostgreSQL's single `ALTER TABLE ... DROP COLUMN`, which is itself a fast metadata-only operation.
- Space isn't reclaimed immediately in PostgreSQL; reuse happens via subsequent DML, or run `VACUUM FULL` to reclaim now (note: `VACUUM FULL` takes an exclusive lock and rewrites the table).
- No equivalent to `USER_UNUSED_COL_TABS`; verify drops via `INFORMATION_SCHEMA.COLUMNS`.
