# Invisible Indexes

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.invisible.html

**Conversion category:** Blocked (one-star feature compatibility)
**SCT automation:** No automation. Indexes action code index. PostgreSQL doesn't support invisible indexes.

## Oracle
An invisible index is maintained during DML but **ignored by the optimizer** by default. Common uses:
- Test the effect of dropping an index without actually dropping it.
- Use a specific index for certain operations/modules without affecting the whole application.
- Add an index on columns that already have an index.

The optimizer can be forced to use invisible indexes by setting `OPTIMIZER_USE_INVISIBLE_INDEXES = true`, or via a query HINT.

```sql
ALTER INDEX idx_name INVISIBLE;
ALTER INDEX idx_name VISIBLE;
CREATE INDEX idx_name ON employees(first_name) INVISIBLE;

SELECT TABLE_OWNER, INDEX_NAME FROM DBA_INDEXES
  WHERE VISIBILITY = 'INVISIBLE';
```

## PostgreSQL
Amazon Aurora PostgreSQL provides **no directly comparable** alternative for Oracle invisible indexes.

## Conversion notes
- No equivalent in PostgreSQL/Aurora. PostgreSQL does not allow an index to exist but be ignored by the planner.
- The `hypopg` extension (hypothetical indexes) addresses a related "what-if" use case but is **not supported on Aurora PostgreSQL**.
- To emulate "test dropping an index," you must actually drop/recreate it, or use a non-production environment.
