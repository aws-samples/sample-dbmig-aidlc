# Oracle Table Statistics and MySQL Managing Statistics

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tuning.statistics.html

**Conversion category:** Assisted (★★★ — three-star feature compatibility)
**SCT automation:** N/A

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

- Statistics are created for **indexes only** — no independent statistics on non-indexed columns.
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

- Unlike Oracle, Aurora MySQL collects only **density information** — no detailed key-distribution histograms. This matters when troubleshooting plans sensitive to specific parameter values.
- Statistics collection is managed at the **table level only**; you cannot manage individual statistics objects or columns. Usually not a migration blocker.
- Aurora MySQL maintains statistics implicitly for every index; there is no separate column-statistics or auto-create-statistics concept.

### Feature mapping (Oracle `DBMS_STATS` → Aurora MySQL)

| Feature | Aurora MySQL | Comments |
|---|---|---|
| Column statistics | N/A | |
| Index statistics | Implicit with every index | Maintained automatically for every table index. |
| Refresh/update statistics | `ANALYZE TABLE` | Minimal scope is the entire table; no per-statistic control. |
| Auto create statistics | N/A | |
| Auto update statistics | `STATS_AUTO_RECALC` table option | |
| Statistics sampling | `STATS_SAMPLE_PAGES` table option | Page count only, not a percentage. |
| Full scan refresh | N/A | A very large `STATS_SAMPLE_PAGES` may serve the same purpose. |
| Non-persistent statistics | `STATS_PERSISTENT=0` table option | |
