# Managing statistics for T-SQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tsql.managingstatistics.html

**Conversion category:** Manual (Three star feature compatibility — no automation)
**SCT automation:** No automation

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

Aurora MySQL supports persistent (default, written to disk, survives restart — recommended for plan stability) and non-persistent (in-memory) optimizer statistics. Statistics are created **for indexes only** — no independent column statistics.

The global `innodb_stats_persistent` parameter is not settable in Aurora MySQL (requires `SUPER`); control per-table with `STATS_PERSISTENT = 1`. Auto-refresh via global `innodb_stats_auto_recalc` (ON), or per-table `STATS_AUTO_RECALC=1`. Force refresh with `ANALYZE TABLE` (table-level only; use `NO_WRITE_TO_BINLOG`/`LOCAL` to avoid replication; `ALTER TABLE … ANALYZE PARTITION` for partitions).

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

- Aurora MySQL collects only **density** information — no detailed key-distribution histograms. Run plans aren't affected by specific parameter values.
- Statistics are managed at the **table level** only — no per-column or per-statistic control.
- No independent column statistics (`CREATE STATISTICS` has no equivalent); statistics exist implicitly for every index.
- `STATS_SAMPLE_PAGES` uses a page count, not a percentage; a very large value approximates `FULLSCAN`.

| Feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Column statistics | `CREATE STATISTICS` | N/A | |
| Index statistics | Implicit per index | Implicit per index | Auto-maintained |
| Refresh/update | `UPDATE STATISTICS`, `sp_updatestats` | `ANALYZE TABLE` | Table-level only |
| Auto create | `AUTO_CREATE_STATISTICS` | N/A | |
| Auto update | `AUTO_UPDATE_STATISTICS` | `STATS_AUTO_RECALC` | |
| Sampling | `SAMPLE` option | `STATS_SAMPLE_PAGES` | Pages, not percent |
| Full scan refresh | `FULLSCAN` option | N/A | Large `STATS_SAMPLE_PAGES` approximates |
| Non-persistent statistics | N/A | `STATS_PERSISTENT=0` | |
