# Managing statistics for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.managingstatistics.html

**Conversion category:** Manual (Three star feature compatibility — no automation)
**SCT automation:** No automation

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected 'no column statistics' (histograms verified on both), SET GLOBAL limits, manual histogram refresh (AUTO UPDATE ignored on 8.4.7+, syntax error on 3.x — verified), no edits to innodb stats tables (verified).

## SQL Server

Statistics support the cost-based query optimizer. Stored as BLOBs in system tables; contain histograms (first column only) and distribution info, collected by full scan or sampling. View via `DBCC SHOW_STATISTICS` or `sys.dm_db_stats_properties` / `sys.dm_db_stats_histogram`. Supports filtered statistics (`WHERE` predicate). Auto-managed by default via `AUTO_CREATE_STATISTICS` and `AUTO_UPDATE_STATISTICS` (and `AUTO_UPDATE_STATISTICS_ASYNC`).

### Syntax

```sql
CREATE STATISTICS <Statistics Name>
ON <Table Name> (<Column> [,...])
[WHERE <Filter Predicate>]
[WITH <Statistics Options>];
```

### Examples

```sql
CREATE STATISTICS MyStatistics
ON MyTable (Col1, Col2)
WITH FULLSCAN, NORECOMPUTE;

UPDATE STATISTICS MyTable(MyStatistics)
WITH SAMPLE 50 PERCENT;

DBCC SHOW_STATISTICS ('MyTable','MyStatistics');

ALTER DATABASE MyDB SET AUTO_CREATE_STATS OFF;
```

## MySQL

Aurora MySQL supports persistent (default, written to disk, survives restart — recommended for plan stability) and non-persistent (in-memory) optimizer statistics. Index statistics are created automatically for every index; *(corrected)* MySQL 8 also has **column histograms** (`ANALYZE TABLE t UPDATE HISTOGRAM ON col WITH n BUCKETS`, verified on 3.13 and 8.4.8), the equivalent of `CREATE STATISTICS` on a non-indexed column.

The global `innodb_stats_persistent` (ON by default, verified) cannot be changed with `SET GLOBAL` by the master user; use the parameter group, or per-table `STATS_PERSISTENT = 1`. Auto-refresh via global `innodb_stats_auto_recalc` (ON), or per-table `STATS_AUTO_RECALC=1`. Force refresh with `ANALYZE TABLE` (table-level only; use `NO_WRITE_TO_BINLOG`/`LOCAL` to avoid replication; `ALTER TABLE … ANALYZE PARTITION` for partitions).

View metadata: `INFORMATION_SCHEMA.STATISTICS`; detailed: `innodb_table_stats`, `innodb_index_stats`.

### Syntax

```sql
ANALYZE [NO_WRITE_TO_BINLOG | LOCAL] TABLE <Table Name> [,...];

CREATE TABLE ( <Table Definition> ) | ALTER TABLE <Table Name>
STATS_PERSISTENT = <1|0>,
STATS_AUTO_RECALC = <1|0>,
STATS_SAMPLE_PAGES = <Statistics Sampling Size>;
```

### Examples

```sql
CREATE TABLE MyTable
(
    Col1 INT NOT NULL AUTO_INCREMENT,
    Col2 VARCHAR(255),
    DateCol DATETIME,
    PRIMARY KEY (Col1),
    INDEX IDX_DATE (DateCol)
) ENGINE=InnoDB,
STATS_PERSISTENT=1,
STATS_AUTO_RECALC=1,
STATS_SAMPLE_PAGES=25;

ANALYZE TABLE MyTable1, MyTable2;

ALTER TABLE MyTable STATS_PERSISTENT=0;
```

## Conversion notes

- Index statistics hold density; **histograms** add value distribution for columns (singleton or equi-height), visible in `information_schema.COLUMN_STATISTICS`. `CREATE STATISTICS` on a non-indexed column → `UPDATE HISTOGRAM`; on several columns → no multi-column histogram (consider a composite index).
- Histograms are **not maintained automatically**: `AUTO_UPDATE_STATISTICS` → schedule `ANALYZE TABLE … UPDATE HISTOGRAM` in an event. On Aurora MySQL 8.4.7+ `AUTO UPDATE` is ignored with a warning; on 3.x it is a syntax error (both verified).
- The master user cannot edit `mysql.innodb_table_stats`/`innodb_index_stats` (error 1044, verified).
- Run `ANALYZE TABLE` on all tables after the bulk load, before performance testing.
- `STATS_SAMPLE_PAGES` uses a page count, not a percentage; a very large value approximates `FULLSCAN`.

| Feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Column statistics | `CREATE STATISTICS` | `ANALYZE TABLE … UPDATE HISTOGRAM` | single column, manual refresh |
| Index statistics | Implicit per index | Implicit per index | Auto-maintained |
| Refresh/update | `UPDATE STATISTICS`, `sp_updatestats` | `ANALYZE TABLE` | Table-level only |
| Auto create | `AUTO_CREATE_STATISTICS` | N/A | create histograms explicitly |
| Auto update | `AUTO_UPDATE_STATISTICS` | `STATS_AUTO_RECALC` | |
| Sampling | `SAMPLE` option | `STATS_SAMPLE_PAGES` | Pages, not percent |
| Full scan refresh | `FULLSCAN` option | N/A | Large `STATS_SAMPLE_PAGES` approximates |
| Non-persistent statistics | N/A | `STATS_PERSISTENT=0` | |
