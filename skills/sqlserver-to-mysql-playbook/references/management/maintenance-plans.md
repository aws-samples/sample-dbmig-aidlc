# Maintenance plans

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.management.maintenanceplans.html

**Conversion category:** Automatic (Three star feature compatibility)
**SCT automation:** N/A

## SQL Server

A maintenance plan is a set of automated tasks to optimize a database, run regular backups, and ensure consistency. Plans are implemented as SSIS packages run by SQL Server Agent jobs (manual or scheduled). Typical tasks:
* Back up database and transaction log files.
* Clean up backup files per retention policies.
* Database consistency checks.
* Rebuild/reorganize indexes.
* Shrink a database (remove empty pages).
* Update statistics for the query optimizer.
* Run SQL Server Agent jobs for custom actions / T-SQL tasks.

Manage via the Maintenance Plan Wizard, Maintenance Plan Design Surface, SSMS Object Explorer, and T-SQL system stored procedures.

**Deprecated DBCC commands** (as of SQL Server 2008 R2):

| Deprecated DBCC command | Use instead |
|---|---|
| `DBCC DBREINDEX` | `ALTER INDEX … REBUILD` |
| `DBCC INDEXDEFRAG` | `ALTER INDEX … REORGANIZE` |
| `DBCC SHOWCONTIG` | `sys.dm_db_index_physical_stats` |

Examples:

```sql
-- Enable Agent XPs (off by default)
EXEC [sys].[sp_configure] @configname = 'show advanced options', @configvalue = 1; RECONFIGURE;
EXEC [sys].[sp_configure] @configname = 'agent xps', @configvalue = 1; RECONFIGURE;

USE msdb;
-- Add the job
EXEC dbo.sp_add_job @job_name = N'Index Maintenance IDX1', @enabled = 1,
    @description = N'Optimize IDX1 for INSERT';
-- Add a T-SQL job step
EXEC dbo.sp_add_jobstep @job_name = N'Index Maintenance IDX1',
    @step_name = N'Rebuild IDX1 to 50 percent fill', @subsystem = N'TSQL',
    @command = N'Use MyDatabase; ALTER INDEX IDX1 ON Schema.Table REBUILD WITH (FILL_FACTOR = 50)',
    @retry_attempts = 5, @retry_interval = 5;
-- Add a schedule (daily at 01:00)
EXEC dbo.sp_add_schedule @schedule_name = N'Daily0100', @freq_type = 4,
    @freq_interval = 1, @active_start_time = 010000;
-- Attach schedule to job
EXEC sp_attach_schedule @job_name = N'Index Maintenance IDX1', @schedule_name = N'Daily0100';
```

## MySQL

Amazon RDS performs automated backups via storage volume snapshots (entire instances, not individual databases), taken during the backup window and retained per the backup retention period. Point-in-time restore is supported within the retention period. The instance must be ACTIVE for automated backups. Manual snapshots can be taken via console/CLI/API.

### Backups (examples)

**Create a manual snapshot:** RDS console → **Databases** → choose instance → **Instance actions** → **Take snapshot**.

**Restore from a snapshot:** RDS console → **Snapshots** → choose snapshot → **Actions** → **Restore snapshot** (creates a new instance). Point-in-time restore is also supported.

### Rebuild / reorganize indexes

```sql
-- Similar to SQL Server REORGANIZE
OPTIMIZE TABLE MyTable;

-- Full table rebuild with secondary indexes (null altering action)
ALTER TABLE MyTable FORCE;
ALTER TABLE MyTable ENGINE = InnoDB;
```

### Database consistency checks

```sql
CHECK TABLE <table name> [FOR UPGRADE | QUICK]
```

`FOR UPGRADE` checks compatibility with the current MySQL version; `QUICK` skips row scans for incorrect links (use `QUICK` for routine checks). When an error is found, the table is marked corrupted until repaired.

### Converting deprecated DBCC commands

| Deprecated DBCC command | Aurora MySQL equivalent |
|---|---|
| `DBCC DBREINDEX` | `ALTER TABLE … FORCE` |
| `DBCC INDEXDEFRAG` | `OPTIMIZE TABLE` |
| `DBCC SHOWCONTIG` | `CHECK TABLE` |

### Shrinking data files

Aurora MySQL uses one file per table (not one set per database), so there's no need to shrink an entire database — rebuilding a table optimizes its file size.

### Update statistics

Aurora MySQL uses persistent and non-persistent statistics. Persistent statistics survive restarts and give better plan stability. Controls:
* `innodb_stats_auto_recalc` — auto-update statistics when table changes cross a threshold.
* `STATS_PERSISTENT`, `STATS_AUTO_RECALC`, `STATS_SAMPLE_PAGES` clauses in `CREATE TABLE`/`ALTER TABLE`.
* View stats in `mysql.innodb_table_stats` / `mysql.innodb_index_stats` (and `last_update` column); modify these tables to force/test plans.

## Summary

| Task | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Rebuild/reorganize indexes | `ALTER INDEX` / `ALTER TABLE` | `OPTIMIZE TABLE` / `ALTER TABLE` | |
| Shrink data files | `DBCC SHRINKDATABASE` / `SHRINKFILE` | One file per table; rebuild optimizes size | Not needed |
| Update statistics | `UPDATE STATISTICS` / `sp_updatestats` | Set `innodb_stats_auto_recalc = ON` in parameter group | |
| Consistency checks | `DBCC CHECKDB` / `CHECKTABLE` | `CHECK TABLE` | |
| Back up DB and log files | `BACKUP DATABASE` / `BACKUP LOG` | Automated backups and snapshots | RDS-managed |
| Run Agent jobs for custom actions | `sp_start_job`, scheduled | Not supported | |

## Conversion notes
- AWS service replacement: SQL Server Agent maintenance plans / backups → **Amazon RDS automated backups and snapshots**; table maintenance → SQL commands.
- Index maintenance: `ALTER INDEX REBUILD/REORGANIZE` → `ALTER TABLE … FORCE` / `OPTIMIZE TABLE`.
- Consistency: `DBCC CHECKDB/CHECKTABLE` → `CHECK TABLE`.
- No database shrink needed (per-table files).
- Statistics auto-recalc via `innodb_stats_auto_recalc`.
- No equivalent to running Agent jobs for custom scheduled actions — use Aurora MySQL Events or external schedulers (see Agent reference).
