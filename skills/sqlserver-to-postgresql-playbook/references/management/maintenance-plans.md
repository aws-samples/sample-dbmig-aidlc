# Maintenance plans

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.maintenanceplans.html

**Conversion category:** N/A (three-star feature compatibility)
**SCT automation:** N/A

Key difference: Backups use Amazon RDS services; table maintenance uses SQL commands.

## SQL Server

A maintenance plan is a set of automated tasks to optimize a database, back it up, and check for inconsistencies. Plans are implemented as SSIS packages run by SQL Server Agent jobs (manual or scheduled).

Typical tasks:
- Back up database and transaction log files.
- Clean up old backup files per retention policy.
- Perform database consistency checks.
- Rebuild or reorganize indexes.
- Shrink a database (remove empty pages).
- Update statistics for the query optimizer.
- Run SQL Server Agent jobs / T-SQL tasks.

Managed via the Maintenance Plan Wizard, Design Surface, Object Explorer, or T-SQL system stored procedures.

Deprecated DBCC index/table maintenance (since 2008 R2):

| Deprecated DBCC command | Use instead |
|---|---|
| `DBCC DBREINDEX` | `ALTER INDEX … REBUILD` |
| `DBCC INDEXDEFRAG` | `ALTER INDEX … REORGANIZE` |
| `DBCC SHOWCONTIG` | `sys.dm_db_index_physical_stats` |

Example — T-SQL maintenance plan for a single index rebuild:

```sql
-- Enable Agent XPs (disabled by default)
EXEC [sys].[sp_configure] @configname = 'show advanced options', @configvalue = 1; RECONFIGURE;
EXEC [sys].[sp_configure] @configname = 'agent xps', @configvalue = 1; RECONFIGURE;

USE msdb;

-- Add the job
EXEC dbo.sp_add_job @job_name = N'Index Maintenance IDX1', @enabled = 1,
    @description = N'Optimize IDX1 for INSERT';

-- Add the T-SQL job step
EXEC dbo.sp_add_jobstep @job_name = N'Index Maintenance IDX1',
    @step_name = N'Rebuild IDX1 to 50 percent fill', @subsystem = N'TSQL',
    @command = N'Use MyDatabase; ALTER INDEX IDX1 ON Schema.Table REBUILD WITH (FILL_FACTOR = 50)',
    @retry_attempts = 5, @retry_interval = 5;

-- Add a daily schedule at 01:00 AM
EXEC dbo.sp_add_schedule @schedule_name = N'Daily0100', @freq_type = 4,
    @freq_interval = 1, @active_start_time = 010000;

-- Attach the schedule to the job
EXEC sp_attach_schedule @job_name = N'Index Maintenance IDX1', @schedule_name = N'Daily0100';
```

## PostgreSQL

Amazon RDS performs automated backups by creating storage-volume snapshots of entire instances (not individual databases), during the backup window, retained per the backup retention period. The instance state must be ACTIVE for automated backups. Manual snapshots can be taken via the console, AWS CLI, or AWS API. Point-in-time restore is also supported.

Examples:
- **Create a manual snapshot (console):** RDS → Databases → choose your Aurora PostgreSQL instance → Instance actions → **Take snapshot**.
- **Restore a snapshot (console):** RDS → Snapshots → choose the snapshot → Actions → **Restore snapshot** (creates a new instance) → complete the wizard → **Restore DB Instance**.

For all other maintenance tasks, use a third-party or custom application scheduler.

**Rebuild / reorganize tables** — Aurora PostgreSQL supports `VACUUM`, `ANALYZE`, and `REINDEX` (similar to SQL Server's index REORGANIZE):

```sql
VACUUM MyTable;   -- reclaims storage
ANALYZE MyTable;  -- collects statistics
REINDEX TABLE MyTable;  -- recreates all indexes
```

Convert deprecated DBCC commands:

| Deprecated DBCC command | Aurora PostgreSQL equivalent |
|---|---|
| `DBCC DBREINDEX` | `REINDEX INDEX` or `REINDEX TABLE` |
| `DBCC INDEXDEFRAG` | `VACUUM table_name` or `VACUUM table_name column_name` |

### Summary

| Task | SQL Server | Aurora PostgreSQL |
|---|---|---|
| Rebuild or reorganize indexes | `ALTER INDEX` or `ALTER TABLE` | `REINDEX INDEX` or `REINDEX TABLE` |
| Decrease data file size (remove empty pages) | `DBCC SHRINKDATABASE` / `DBCC SHRINKFILE` | `VACUUM` |
| Update statistics | `UPDATE STATISTICS` or `sp_updatestats` | `ANALYZE` |
| Database consistency checks | `DBCC CHECKDB` / `DBCC CHECKTABLE` | N/A |
| Back up database and transaction log | `BACKUP DATABASE` / `BACKUP LOG` | Automatically (e.g., via AWS CLI / RDS snapshots) |
| Run Agent jobs for custom actions | `sp_start_job` / scheduled | N/A |

## Conversion notes

- AWS service replacement: Amazon RDS automated snapshots + point-in-time restore replace `BACKUP DATABASE`/`BACKUP LOG` maintenance tasks.
- Table maintenance maps to SQL commands: `VACUUM` (reclaim space / shrink), `ANALYZE` (statistics), `REINDEX` (rebuild indexes).
- No equivalent for database consistency checks (`DBCC CHECKDB`) or in-engine Agent job scheduling — use external/custom schedulers (or scheduled Lambda).
- Snapshots are instance-level, not per-database.
