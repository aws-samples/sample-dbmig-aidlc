# Oracle and PostgreSQL Table Statistics

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tuning.statistics.html

**Conversion category:** Assisted
**SCT automation:** N/A (three-star feature compatibility; syntax and option differences, similar functionality)

Table statistics describe data distribution and storage characteristics (row counts, data sizes, index usage) and let the query optimizer make informed plan decisions.

## Oracle

Oracle collects statistics such as number of table rows, number of table blocks, number of distinct values or nulls, and data distribution histograms. The `DBMS_STATS` package manages statistics, collected automatically or manually.

**Automatic optimizer statistics collection.** By default Oracle collects table and index statistics during predefined maintenance windows via the scheduler and automated maintenance tasks. It uses data modification monitoring (tracking approximate counts of `INSERT`, `UPDATE`, `DELETE`) to determine which statistics to collect. Oracle 19 adds **real-time statistics** gathered during regular DML so statistics don't go stale, plus **High-Frequency Automatic Optimizer Statistics Collection** for stale objects.

**Manual optimizer statistics collection** can be done at several levels:

| Statistics level | Description |
|---|---|
| `GATHER_INDEX_STATS` | Index statistics. |
| `GATHER_TABLE_STATS` | Table, column, and index statistics. |
| `GATHER_SCHEMA_STATS` | Statistics for all objects in a schema. |
| `GATHER_DICTIONARY_STATS` | Statistics for all dictionary objects. |
| `GATHER_DATABASE_STATS` | Statistics for all objects in a database. |

Collect statistics at the table level (`HR` schema, `EMPLOYEES` table):

```sql
BEGIN
DBMS_STATS.GATHER_TABLE_STATS('HR','EMPLOYEES');
END;
/

PL/SQL procedure successfully completed.
```

Collect statistics at a specific column level (`DEPARTMENT_ID` column):

```sql
BEGIN
DBMS_STATS.GATHER_TABLE_STATS('HR','EMPLOYEES',
METHOD_OPT=>'FOR COLUMNS department_id');
END;
/

PL/SQL procedure successfully completed.
```

See *Optimizer Statistics Concepts* in the Oracle documentation.

## PostgreSQL

Use the `ANALYZE` command to collect statistics for a database, table, or specific column. It supports efficient plan generation by the planner.
* **Histograms** — `ANALYZE` collects column-value statistics and builds an approximate data-distribution histogram per column.
* **Pages and rows** — collects the number of database pages and rows per table.
* **Data sampling** — for large tables, `ANALYZE` takes random samples rather than scanning every row, so it scans very large tables quickly.
* **Granularity** — `ANALYZE` with no parameter examines every table in the current schema; supplying a table or column name limits it to that table or column.

**Automatic statistics collection.** PostgreSQL's **autovacuum daemon** automates `ANALYZE` (and `VACUUM`), scanning for tables with large data modifications to collect current statistics. It is controlled by several parameters. Per-table storage parameters can trigger autovacuum sooner or later, set via `CREATE TABLE` or `ALTER TABLE`:

```sql
ALTER TABLE custom_autovaccum
  SET (autovacuum_enabled = true,
    autovacuum_vacuum_cost_delay = 10ms,
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005);
```

This enables autovacuum for the table, makes the process sleep 10 ms each run, and adds 1% of table size to `autovacuum_vacuum_threshold` and 0.5% to `autovacuum_analyze_threshold` when deciding whether to trigger a VACUUM.

**Manual statistics collection** via `ANALYZE` at database, table, or column level. Notes:
* `ANALYZE` on indexes is not currently supported.
* `ANALYZE` requires only a read-lock on the target table, so it can run in parallel with other table activity.
* For large tables, `ANALYZE` samples the contents; the sample size is configured via `default_statistics_target` (default 100 entries). Raising it improves planner estimate accuracy at the cost of more space in `pg_statistic`.

Examples:

```sql
-- Entire database
ANALYZE;

-- Specific table (VERBOSE shows progress)
ANALYZE VERBOSE EMPLOYEES;

-- Specific column
ANALYZE EMPLOYEES (HIRE_DATE);

-- Set/reset per-column statistics target
ALTER TABLE EMPLOYEES ALTER COLUMN SALARY SET STATISTICS 150;
ALTER TABLE EMPLOYEES ALTER COLUMN SALARY SET STATISTICS -1;

-- View and change default_statistics_target, then analyze
SHOW default_statistics_target ;
SET default_statistics_target to 150;
ANALYZE EMPLOYEES;

-- View last time statistics were collected
SELECT relname, last_analyze FROM pg_stat_all_tables;
```

Larger statistics targets increase `ANALYZE` time but improve planner-statistics quality, potentially yielding better execution plans.

See *ANALYZE* and *The Autovacuum Daemon* in the PostgreSQL documentation.

## Conversion notes

Feature mapping (Oracle → PostgreSQL):

| Feature | Oracle | PostgreSQL |
|---|---|---|
| Analyze a specific table | `BEGIN dbms_stats.gather_table_stats(ownname=>'hr', tabname=>'employees', ...); END;` | `ANALYZE EMPLOYEES;` |
| Analyze with sampling | Percentage of rows: `ESTIMATE_PERCENT=>100` | Number of entries: `SET default_statistics_target to 150; ANALYZE EMPLOYEES;` |
| Collect statistics for a schema | `BEGIN EXECUTE DBMS_STATS.GATHER_SCHEMA_STATS(ownname => 'HR'); END` | `ANALYZE;` |
| View last collection time | `select owner, table_name, last_analyzed;` | `select relname, last_analyze from pg_stat_all_tables;` |

- Oracle uses the `DBMS_STATS` PL/SQL package; PostgreSQL uses the SQL `ANALYZE` command — convert procedure calls to `ANALYZE` statements.
- Sampling model differs: Oracle controls sampling by **percentage of rows** (`ESTIMATE_PERCENT`); PostgreSQL controls it by **number of entries** (`default_statistics_target`, default 100), settable globally, per session, or per column.
- Automatic collection: Oracle scheduler maintenance windows / real-time stats (19c) → PostgreSQL **autovacuum daemon** (tune via global params or per-table `ALTER TABLE ... SET (autovacuum_*)`).
- PostgreSQL `ANALYZE` does **not** support analyzing indexes directly (Oracle `GATHER_INDEX_STATS` has no direct equivalent).
- `ANALYZE` takes only a read lock, allowing concurrent table activity.
- After bulk loads or major data changes during migration, run `ANALYZE` explicitly to avoid stale statistics and poor initial plans rather than waiting for autovacuum.
