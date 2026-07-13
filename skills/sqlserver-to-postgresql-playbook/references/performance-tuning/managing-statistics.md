# Managing Statistics

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tuning.statistics.html

**Conversion category:** Assisted (three-star feature compatibility — similar functionality, syntax/option differences)
**SCT automation:** N/A

Both engines use statistics (histograms, value distributions, page/row counts) to drive their cost-based optimizers. Functionality is similar; the syntax and configuration options differ.

## SQL Server

Statistics objects support the cost-based query optimizer. They are stored as BLOBs in system tables and contain histograms and distribution data for one or more columns (a histogram is built for the first column only). They are collected by full table scan or by sampling a percentage of rows.

- View statistics: `DBCC SHOW_STATISTICS`, or the `sys.dm_db_stats_properties` and `sys.dm_db_stats_histogram` system views.
- Filtered statistics support a `WHERE` predicate to refine histogram granularity (e.g., excluding NULLs).
- Automatic management (default) is controlled by `AUTO_CREATE_STATISTICS` and `AUTO_UPDATE_STATISTICS`. With auto-create on, missing beneficial statistics are created when a query is submitted. `AUTO_UPDATE_STATISTICS_ASYNC` chooses synchronous (query waits) vs asynchronous refresh (triggering run does not benefit).
- With `AUTO_UPDATE_STATISTICS` on, statistics are recalculated when stale (after significant data modifications).

Syntax:

```sql
CREATE STATISTICS <Statistics Name>
ON <Table Name> (<Column> [,...])
[WHERE <Filter Predicate>]
[WITH <Statistics Options>;
```

Create multi-column statistics with full scan and no auto-refresh:

```sql
CREATE STATISTICS MyStatistics
ON MyTable (Col1, Col2)
WITH FULLSCAN, NORECOMPUTE;
```

Update statistics with a 50% sampling rate:

```sql
UPDATE STATISTICS MyTable(MyStatistics)
WITH SAMPLE 50 PERCENT;
```

View the histogram and data:

```sql
DBCC SHOW_STATISTICS ('MyTable','MyStatistics');
```

Turn off automatic statistics creation for a database:

```sql
ALTER DATABASE MyDB SET AUTO_CREATE_STATS OFF;
```

## PostgreSQL

Use `ANALYZE` to collect statistics at database, table, or column level for the query planner:

- **Histograms** — approximate per-column data distribution.
- **Pages and Rows** — number of pages and rows per table.
- **Data Sampling** — large tables are sampled randomly rather than fully scanned, keeping `ANALYZE` fast.
- **Granularity** — `ANALYZE` with no arguments examines every table in the current schema; supplying a table or column narrows the scope.
- `ANALYZE` on indexes is not supported. It takes only a read-lock and can run concurrently with other table activity.
- Sample size is governed by `default_statistics_target` (default 100 entries); higher values improve planner estimates at the cost of more space in `pg_statistic` and longer `ANALYZE` runs.

**Automatic collection** — the `AUTOVACUUM` daemon runs `ANALYZE` (and `VACUUM`) automatically against tables showing large data changes. Per-table storage parameters tune when it fires:

```sql
ALTER TABLE custom_autovaccum SET (autovacuum_enabled = true, autovacuum_vacuum_cost_delay = 10ms, autovacuum_vacuum_scale_factor = 0.01, autovacuum_analyze_scale_factor = 0.005);
```

This enables autovacuum for the table, sleeps 10 ms per run, and adds 1% of table size to the vacuum threshold and 0.5% to the analyze threshold when deciding to trigger.

**Manual collection / extended statistics** — PostgreSQL 10+ adds `CREATE STATISTICS` to build an extended statistics object that tracks more detailed, cross-column data.

Gather statistics for the entire database:

```sql
ANALYZE;
```

Gather statistics for a specific table (with progress):

```sql
ANALYZE VERBOSE EMPLOYEES;
```

Gather statistics for a specific column:

```sql
ANALYZE EMPLOYEES (HIRE_DATE);
```

Set / reset per-column statistics target:

```sql
ALTER TABLE EMPLOYEES ALTER COLUMN SALARY SET STATISTICS 150;

ALTER TABLE EMPLOYEES ALTER COLUMN SALARY SET STATISTICS -1;
```

View and change `default_statistics_target`, then analyze:

```sql
SHOW default_statistics_target ;
SET default_statistics_target to 150;
ANALYZE EMPLOYEES ;
```

View the last time statistics were collected:

```sql
select relname, last_analyze from pg_stat_all_tables;
```

## Conversion notes

- Three-star (assisted) compatibility: similar functionality, differing syntax and options.
- Analyze a table: SQL Server `CREATE STATISTICS MyStatistics ON MyTable (Col1, Col2)` → PostgreSQL `ANALYZE EMPLOYEES;`.
- Sampled collection: SQL Server `UPDATE STATISTICS ... WITH SAMPLE 50 PERCENT` → PostgreSQL controls sample size via `SET default_statistics_target to 150; ANALYZE EMPLOYEES;` (per-row percentage is not specified directly).
- View last collection: SQL Server `DBCC SHOW_STATISTICS('MyTable','MyStatistics')` → PostgreSQL `select relname, last_analyze from pg_stat_all_tables;`.
- Automatic refresh: SQL Server `AUTO_CREATE_STATISTICS`/`AUTO_UPDATE_STATISTICS` → PostgreSQL `AUTOVACUUM` daemon (also handles `VACUUM`), tuned with per-table `autovacuum_*` storage parameters.
- SQL Server filtered statistics (`WHERE` predicate) have no direct PostgreSQL equivalent; PostgreSQL 10+ `CREATE STATISTICS` provides extended (multi-column) statistics instead.
- PostgreSQL cannot `ANALYZE` indexes; SQL Server statistics are tied to indexes and columns. PostgreSQL statistics granularity is tuned with `default_statistics_target` (global/session) or per-column `SET STATISTICS`.
