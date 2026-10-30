# Oracle Table Statistics and MySQL Managing Statistics

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tuning.statistics.html

**Conversion category:** Assisted (★★★ — three-star feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Corrected 'no histograms' (MySQL 8 histograms verified on both versions); 8.4.7+ AUTO UPDATE ignored and 3.x syntax error (verified); verified stats defaults; analyze after bulk load.

Key differences: Syntax and option differences, similar functionality.

## Oracle

Table statistics let the query optimizer make informed run-plan decisions. Oracle provides the `DBMS_STATS` package to manage statistics, collected automatically or manually. Statistics typically collected on tables/indexes:

- Number of table rows.
- Number of table blocks.
- Number of distinct values or nulls.
- Data distribution histograms.

### Automatic optimizer statistics collection

By default Oracle collects table/index statistics during predefined maintenance windows via the scheduler and automated maintenance tasks, using data modification monitoring (approximate count of `INSERT`/`UPDATE`/`DELETE`) to decide which stats to collect. Oracle 19 adds real-time statistics during regular DML so stats don't go stale, plus high-frequency automatic collection for stale objects.

### Manual optimizer statistics collection

| Statistics level | Description |
|---|---|
| `GATHER_INDEX_STATS` | Index statistics |
| `GATHER_TABLE_STATS` | Table, column, and index statistics |
| `GATHER_SCHEMA_STATS` | Statistics for all objects in a schema |
| `GATHER_DICTIONARY_STATS` | Statistics for all dictionary objects |
| `GATHER_DATABASE_STATS` | Statistics for all objects in a database |

### Examples

Collect statistics at the table level:

```sql
BEGIN
DBMS_STATS.GATHER_TABLE_STATS('HR','EMPLOYEES');
END;
/
-- PL/SQL procedure successfully completed.
```

Collect statistics at a specific column level:

```sql
BEGIN
DBMS_STATS.GATHER_TABLE_STATS('HR','EMPLOYEES',
METHOD_OPT=>'FOR COLUMNS department_id');
END;
/
-- PL/SQL procedure successfully completed.
```

## MySQL

Aurora MySQL supports two modes: **Persistent Optimizer Statistics** (written to disk, survive restart — the Aurora MySQL default, recommended for plan stability) and **Non-Persistent Optimizer Statistics** (kept in memory, recreated after restart).

- InnoDB index statistics are created for **indexes**; for non-indexed columns MySQL 8 adds **histograms** (`ANALYZE TABLE t UPDATE HISTOGRAM ON col WITH n BUCKETS`, verified on 3.13 and 8.4), stored in `information_schema.COLUMN_STATISTICS`. The original playbook (MySQL 5.7) said there were no column statistics.
- Switch mode globally via `innodb_stats_persistent = ON`, or per-table via `STATS_PERSISTENT = 1`. No column-level or statistics-level options.
- View metadata via `INFORMATION_SCHEMA.STATISTICS`; view detailed persistent stats via `innodb_table_stats` and `innodb_index_stats`.
- Auto refresh controlled globally by `innodb_stats_auto_recalc` (`ON` in Aurora MySQL), or per-table via `STATS_AUTO_RECALC=1`.
- Force a refresh with `ANALYZE TABLE` (cannot refresh individual statistics or columns).
- Use `NO_WRITE_TO_BINLOG` (alias `LOCAL`) to avoid replication to secondaries.
- Use `ALTER TABLE … ANALYZE PARTITION` to analyze individual partitions.
- RDS for MySQL 8 adds `INFORMATION_SCHEMA.INNODB_CACHED_INDEXES` (index pages cached in the InnoDB buffer pool per index).

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
-- Create a table with explicit statistics options
CREATE TABLE MyTable
(Col1 INT NOT NULL AUTO_INCREMENT,
Col2 VARCHAR(255),
DateCol DATETIME,
PRIMARY KEY (Col1),
INDEX IDX_DATE (DateCol)
) ENGINE=InnoDB,
STATS_PERSISTENT=1,
STATS_AUTO_RECALC=1,
STATS_SAMPLE_PAGES=25;

-- Refresh all statistics for two tables
ANALYZE TABLE MyTable1, MyTable2;

-- Switch a table to non-persistent statistics
ALTER TABLE MyTable STATS_PERSISTENT=0;
```

## Conversion notes

- Index statistics hold density (cardinality) only; **histograms** give value distribution for columns, like Oracle histograms (singleton or equi-height). Create them for skewed, non-indexed filter columns.
- Histograms are **not maintained automatically**: refresh them with `ANALYZE TABLE … UPDATE HISTOGRAM` in a scheduled job (event). On Aurora MySQL 8.4.7+, `AUTO UPDATE` is ignored with a warning (verified on 8.4.8); on 3.x `AUTO UPDATE` is a syntax error (verified).
- Defaults (verified on both): `innodb_stats_persistent` = ON, `innodb_stats_auto_recalc` = ON (recalculates after ~10% of rows change), `innodb_stats_persistent_sample_pages` = 20. Raise sampling per table (`STATS_SAMPLE_PAGES`) for large skewed tables.
- After a bulk load (`./dbmig migrate-data` or DMS), run `ANALYZE TABLE` on every table before testing plans.
- Statistics collection is managed at the **table level only**; you cannot manage individual statistics objects or columns. Usually not a migration blocker.
- Aurora MySQL maintains statistics implicitly for every index; there is no separate column-statistics or auto-create-statistics concept.

### Feature mapping (Oracle `DBMS_STATS` → Aurora MySQL)

| Feature | Aurora MySQL | Comments |
|---|---|---|
| Column statistics | Histograms (`UPDATE HISTOGRAM`) | Manual refresh only |
| Index statistics | Implicit with every index | Maintained automatically for every table index. |
| Refresh/update statistics | `ANALYZE TABLE` | Minimal scope is the entire table; no per-statistic control. |
| Auto create statistics | N/A | |
| Auto update statistics | `STATS_AUTO_RECALC` table option | |
| Statistics sampling | `STATS_SAMPLE_PAGES` table option | Page count only, not a percentage. |
| Full scan refresh | N/A | A very large `STATS_SAMPLE_PAGES` may serve the same purpose. |
| Non-persistent statistics | `STATS_PERSISTENT=0` table option | |
