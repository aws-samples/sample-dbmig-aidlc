# Invisible Indexes

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.invisible.html

**Conversion category:** Blocked (one-star feature compatibility)
**SCT automation:** No automation. Indexes action code index. PostgreSQL doesn't support invisible indexes.

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): HypoPG is available (corrected), `pg_hint_plan` per-query index hiding, transactional `DROP INDEX` test on clones, `pg_index` hack denied (verified).

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
- The `hypopg` extension (hypothetical indexes) **is available on Aurora PostgreSQL 18** (1.4.2, verified). It covers the "would a new index help?" use case. (The original playbook said it was not supported; that is outdated.)
- To test "what if this existing index were invisible":
  - `pg_hint_plan` (available on Aurora 18): `/*+ NoIndexScan(t idx_name) */` or `/*+ SeqScan(t) */` on the test query hides the index from that statement only, which is the closest equivalent to `OPTIMIZER_USE_INVISIBLE_INDEXES = false` for one query.
  - In a non-production clone: `BEGIN; DROP INDEX idx_name; EXPLAIN …; ROLLBACK;` shows the plan without the index. `DROP INDEX` takes an exclusive lock until rollback, so never run this on a busy production table.
  - Aurora QPM can pin the current plans while you evaluate an index drop.
- Editing `pg_index.indisvalid` directly (a common community hack) is not allowed on Aurora (`permission denied for table pg_index`, verified).
- Default conversion: create Oracle `INVISIBLE` indexes as normal indexes **only if** they will be made visible; otherwise skip them and record the decision.
