# Migration Quick Tips — Oracle → Aurora PostgreSQL

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook — Migration quick tips
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tips.html

A fast-reference list of functional differences administrators and developers new to
PostgreSQL/Aurora commonly hit. Use as a pre-conversion checklist.

## Management
- *Database Snapshot* (Aurora) ≈ Oracle RMAN backup.
- Partitioning uses `INHERITS` tables — managed very differently from Oracle partitions.
- PostgreSQL statistics rely on selectivity only (no detailed key-value distribution);
  parameter values are insignificant to plan choices when troubleshooting.
- Missing features (e.g. sending email) are often replaced by AWS services (Lambda, SES).
- Parameters and backups are managed by Amazon RDS (parameter groups, default comparison).
- High availability via read replicas in a few clicks.
- Database links: `dblink` extension (Oracle-like) or `postgres_fdw` (Foreign Data Wrapper).

## SQL & PL/pgSQL
- Triggers use `NEW` and `OLD` for inserted/deleted row values.
- Cursor status checks are limited — declare an explicit `HANDLER` where needed.
- Run a stored procedure/function with `SELECT`, not `EXECUTE`.
- Run a dynamic string query with Prepared Statements, not `EXECUTE('<string>')`.
- Terminate `IF` blocks with `END IF`; `WHILE..LOOP` with `END LOOP`.
- **Autocommit is ON** by default — turn it off to behave more like Oracle.
- No special UNICODE data types; any string type can use any charset/collation.
- Collations can be set at server/database/column level, **not** table level.
- `DELETE <table>` without `FROM` is invalid — always include `FROM`.
- `SERIAL` column property ≈ Oracle `IDENTITY`.
- Error handling has fewer features; log/alert by inserting into tables or catching errors.
- Native `MERGE` historically unsupported (use `INSERT ... ON CONFLICT` on modern PG; the
  playbook suggests REPLACE / upsert patterns).
- String concatenation with `||` works as in Oracle.
- PostgreSQL is **strict about semicolons** — terminate every statement.
- Modern PostgreSQL supports `CREATE PROCEDURE`; older guidance was function-only (return
  `void`). Confirm against your target version.
- Window/scalar `GREATEST` and `LEAST` may return different results than Oracle — test.
- `SAVEPOINT` / `ROLLBACK TO SAVEPOINT` are not supported inside functions.
- `BFILE`, `ROWID`, `UROWID` are unsupported — redesign with other types.
- Temporary tables are session-scoped and visible only to the creating session.
- No unused or virtual columns; emulate virtual columns with views + functions.
- No automatic/incremental materialized-view `REFRESH` — use triggers.
- Multiple databases per instance — useful for consolidation projects.
- Beware control characters when pasting scripts — PostgreSQL is far more sensitive than
  Oracle and produces hard-to-find syntax errors.

## Conversion notes
These tips overlap with the detailed `sql-plsql/`, `tables-indexes/`, and `special-features/`
references — treat this page as the index of "gotchas" and follow the per-topic file for the
actual conversion pattern and examples.
