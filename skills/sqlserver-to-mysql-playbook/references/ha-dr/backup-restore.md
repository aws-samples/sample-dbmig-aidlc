# Backup and restore design

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.hadr.backuprestore.html

**Conversion category:** N/A (infrastructure / managed-service topic — four-star feature compatibility)
**SCT automation:** No automation (SCT action code index: Backup)

## SQL Server

*Backup* refers to both the process of copying data and the resulting data set used for
safekeeping and disaster recovery. Backups copy SQL Server data and transaction logs to
media (tape, network share, cloud storage, local files); a *restore* copies them back.

SQL Server backs up at the database or sub-database (file/filegroup) level — table backups
aren't supported. Under the `FULL` recovery model, transaction logs must also be backed up,
enabling point-in-time restore. Recovery model is a database-level setting controlling
transaction log management; the three models are `SIMPLE`, `FULL`, and `BULK LOGGED`.

The `RESTORE` process copies data and log pages from a backup, then runs recovery: rolling
forward committed transactions not yet flushed and rolling back uncommitted ones.

Backup types supported:
- **Copy-only backups** — independent of the standard backup chain; one-off backups that
  don't interrupt normal operations.
- **Data backups** — copy data files plus the transaction log activity during the backup
  (whole database or part).
- **Database backup** — a data backup representing the entire database at the point the
  backup finished.
- **Differential backup** — only the extents modified since the last full backup; depends on
  the previous full backup and can't be used alone.
- **Full backup** — a database backup plus transaction log records of activity during backup.
- **Transaction log backups** — log pages only (no data pages) for activity since the last
  full or previous log backup.
- **File backups** — one or more files or filegroups.

SQL Server also supports media families/media sets for mirroring and striping backup
devices, and backup compression (Enterprise 2008+) — smaller footprint and less I/O at the
cost of more CPU.

A `SIMPLE`-mode database can only be restored from full or differential backups; `FULL` and
`BULK LOGGED` also allow restoring transaction log backups to minimize data loss. A typical
restore sequence:
1. Restore the most recent full backup.
2. Restore the most recent differential backup.
3. Restore a set of uninterrupted transaction log backups, in order.
4. Recover the database.

For large databases, SQL Server supports file restore (a set of files) and single data page
restore, except under the `SIMPLE` recovery model.

### Syntax

Backup:

```sql
-- Backing Up a Whole Database
BACKUP DATABASE <Database Name> [ <Files / Filegroups> ] [ READ_WRITE_FILEGROUPS ]
    TO <Backup Devices>
    [ <MIRROR TO Clause> ]
    [ WITH [DIFFERENTIAL ]
    [ <Option List> ][;]

BACKUP LOG <Database Name>
    TO <Backup Devices>
    [ <MIRROR TO clause> ]
    [ WITH <Option List> ][;]

<Option List> =
COPY_ONLY | {COMPRESSION | NO_COMPRESSION } | DESCRIPTION = <Description>
| NAME = <Backup Set Name> | CREDENTIAL | ENCRYPTION | FILE_SNAPSHOT | { EXPIREDATE =
<Expiration Date> | RETAINDAYS = <Retention> }
{ NOINIT | INIT } | { NOSKIP | SKIP } | { NOFORMAT | FORMAT } |
{ NO_CHECKSUM | CHECKSUM } | { STOP_ON_ERROR | CONTINUE_AFTER_ERROR }
{ NORECOVERY | STANDBY = <Undo File for Log Shipping> } | NO_TRUNCATE
ENCRYPTION ( ALGORITHM = <Algorithm> | SERVER CERTIFICATE = <Certificate> | SERVER
ASYMMETRIC KEY = <Key> );
```

Restore:

```sql
RESTORE DATABASE <Database Name> [ <Files / Filegroups> ] | PAGE = <Page ID>
FROM <Backup Devices>
[ WITH [ RECOVERY | NORECOVERY | STANDBY = <Undo File for Log Shipping> } ]
[, <Option List>]
[;]

RESTORE LOG <Database Name> [ <Files / Filegroups> ] | PAGE = <Page ID>
[ FROM <Backup Devices>
[ WITH [ RECOVERY | NORECOVERY | STANDBY = <Undo File for Log Shipping> } ]
[, <Option List>]
[;]

<Option List> =
MOVE <File to Location>
| REPLACE | RESTART | RESTRICTED_USER | CREDENTIAL
| FILE = <File Number> | PASSWORD = <Password>
| { CHECKSUM | NO_CHECKSUM } | { STOP_ON_ERROR | CONTINUE_AFTER_ERROR }
| KEEP_REPLICATION | KEEP_CDC
| { STOPAT = <Stop Time>
| STOPATMARK = <Log Sequence Number>
| STOPBEFOREMARK = <Log Sequence Number>
```

### Examples

```sql
-- Full compressed database backup
BACKUP DATABASE MyDatabase TO DISK='C:\Backups\MyDatabase\FullBackup.bak'
WITH COMPRESSION;

-- Log backup
BACKUP DATABASE MyDatabase TO DISK='C:\Backups\MyDatabase\LogBackup.bak'
WITH COMPRESSION;

-- Partial differential backup
BACKUP DATABASE MyDatabase
    FILEGROUP = 'FileGroup1',
    FILEGROUP = 'FileGroup2'
    TO DISK='C:\Backups\MyDatabase\DB1.bak'
    WITH DIFFERENTIAL;

-- Restore a database to a point in time
RESTORE DATABASE MyDatabase
    FROM DISK='C:\Backups\MyDatabase\FullBackup.bak'
    WITH NORECOVERY;

RESTORE LOG AdventureWorks2012
    FROM DISK='C:\Backups\MyDatabase\LogBackup.bak'
    WITH NORECOVERY, STOPAT = '20180401 10:35:00';

RESTORE DATABASE AdventureWorks2012 WITH RECOVERY;
```

## MySQL

Aurora MySQL continuously backs up all cluster volumes and retains restore data for the
backup retention period. Backups are incremental and support point-in-time restore to any
moment within the retention period (1–35 days, set at create/modify time). Backups incur no
performance impact and cause no service interruption. You can also take manual snapshots
saved beyond the retention period (manual snapshots incur RDS storage charges).

> Note: From Amazon RDS / MySQL 8.0.21, redo logging can be toggled with
> `ALTER INSTANCE {ENABLE|DISABLE} INNODB REDO_LOG` to speed up bulk loads into a new
> instance. The `INNODB_REDO_LOG_ENABLE` privilege controls it; `Innodb_redo_log_enabled`
> status variable monitors it.

### Restoring Data
Recover from automatically retained data or a manual snapshot. The RDS console shows
**Latest Restorable Time** (typically within the last five minutes) and **Earliest
Restorable Time** (end of the retention period). Both display NULL until a cluster restore
completes.

### Restoring Database Backups from Amazon S3
You can restore MySQL 5.7 backups stored on S3 to Aurora MySQL and RDS for MySQL. When
migrating MySQL 5.5/5.6/5.7, copying full and incremental backups to S3 and restoring is
considerably faster than `mysqldump`, which replays SQL statements to recreate the database.

### Backtracking an Aurora DB Cluster
Backtracking rewinds an Aurora MySQL cluster to a specified time *without* restoring from a
backup. It isn't a replacement for backups but offers advantages:
- Easily undo mistakes (e.g., a `DELETE` without a `WHERE`) with minimal service interruption.
- Fast — rewinds in minutes versus hours for a point-in-time restore (which launches a new
  cluster).
- Explore earlier data changes by backtracking back and forth to locate when a change
  occurred.

### Database Cloning
A fast, cost-effective way to create copies. Multiple clones can be made from one cluster
(and clones of clones). Uses a copy-on-write protocol — data is copied only when it changes
on source or clone, so a new clone needs minimal additional storage. Useful for testing
schema/parameter changes, isolating intensive workloads, and dev/test with production data.

### Copying and Sharing Snapshots
Snapshots can be copied/shared within a Region, across Regions, and across accounts. Sharing
grants another account access to restore without copying first. Copying an automated
snapshot to another account: (1) create a manual snapshot from it, (2) copy that manual
snapshot to the other account.

### Backup Storage
Backup storage is the collection of automated and manual snapshots for all instances and
clusters; size is the sum of all individual snapshots. Deleting an instance deletes its
automated backups, but you can create a final snapshot (retained as a manual snapshot;
manual snapshots aren't auto-deleted).

### The Backup Retention Period
Set at cluster creation. Default is 1 day via the RDS API/CLI, 7 days via the Console.
Modifiable any time between 1 and 35 days.

### Disabling Automated Backups
You can't turn off automated backups on Aurora MySQL; retention is managed by the cluster.

### Saving Data to Amazon S3
Aurora MySQL supports proprietary syntax to dump/load directly to/from S3 — efficient since
no intermediate client app handles the export/import.

```sql
SELECT
    [ALL | DISTINCT | DISTINCTROW ]
        [HIGH_PRIORITY]
        [STRAIGHT_JOIN]
        [SQL_SMALL_RESULT] [SQL_BIG_RESULT] [SQL_BUFFER_RESULT]
        [SQL_CACHE | SQL_NO_CACHE] [SQL_CALC_FOUND_ROWS]
    select_expr [, select_expr ...]
    [FROM table_references
        [PARTITION partition_list]
    [WHERE where_condition]
    [GROUP BY {col_name | expr | position}
        [ASC | DESC], ... [WITH ROLLUP]]
    [HAVING where_condition]
    [ORDER BY {col_name | expr | position}
        [ASC | DESC], ...]
    [LIMIT {[offset,] row_count | row_count OFFSET offset}]
    [PROCEDURE procedure_name(argument_list)]
INTO OUTFILE S3 'S3-URI'
[CHARACTER SET charset_name]
    [export_options]
    [MANIFEST {ON | OFF}]
    [OVERWRITE {ON | OFF}]

export_options:
    [{FIELDS | COLUMNS}
        [TERMINATED BY 'string']
        [[OPTIONALLY] ENCLOSED BY 'char']
        [ESCAPED BY 'char']
    ]
    [LINES
        [STARTING BY 'string']
        [TERMINATED BY 'string']
    ]
```

```sql
LOAD DATA FROM S3 [FILE | PREFIX | MANIFEST] 'S3-URI'
    [REPLACE | IGNORE]
    INTO TABLE tbl_name
    [PARTITION (partition_name,...)]
    [CHARACTER SET charset_name]
    [{FIELDS | COLUMNS}
        [TERMINATED BY 'string']
        [[OPTIONALLY] ENCLOSED BY 'char']
        [ESCAPED BY 'char']
    ]
    [LINES
        [STARTING BY 'string']
        [TERMINATED BY 'string']
    ]
    [IGNORE number {LINES | ROWS}]
    [(col_name_or_user_var,...)]
    [SET col_name = expr,...]
```

The `MANIFEST` option of the export creates a JSON file listing the text files produced by
`SELECT … INTO OUTFILE S3`; `LOAD DATA FROM S3` can later use this manifest to reload them.

### Migration Considerations
Moving from a self-managed backup policy to a PaaS like Aurora MySQL is a paradigm shift — no
more transaction logs, filegroups, disk-space, or purge management. RDS provides
continuous backup with point-in-time restore up to 35 days. With Aurora MySQL you only set
the retention period and take manual snapshots for special cases.

### Considerations for Exporting to S3
- Default max file size is 6 GB; the system rolls over to a new file when exceeded. Rows
  never span files, so slight variations from the max are possible.
- `SELECT … INTO OUTFILE S3` is an atomic transaction; on error it rolls back and should be
  rerun. Already-uploaded data isn't deleted on rollback, so a differential approach can
  upload only the remainder.
- For exports larger than 25 GB, AWS recommends splitting into multiple smaller batches.
- Metadata (table schema, file metadata) isn't uploaded to S3.

### Example — Change the Retention Policy to Seven Days
1. Log in to the Management Console, choose **Amazon RDS**, then **Databases**.
2. Choose the relevant DB identifier.
3. Verify current automatic backup settings.
4. Select the writer-role instance and choose **Modify**.
5. In the **Backup** section, select **7 Days**.
6. Choose **Continue**, review the summary, choose scheduled maintenance window or apply
   immediately, then **Modify DB instance**.

## Conversion notes
- Aurora MySQL backups are functionally equivalent to SQL Server's `FULL` recovery model.

| Feature | SQL Server | Aurora MySQL | Comments |
|---|---|---|---|
| Recovery model | `SIMPLE`, `BULK LOGGED`, `FULL` | N/A | Aurora MySQL backups ≈ `FULL` recovery model |
| Backup database | `BACKUP DATABASE` | Automatic and continuous | |
| Partial backup | `BACKUP DATABASE ... FILE=... \| FILEGROUP=...` | N/A | |
| Log backup | `BACKUP LOG` | N/A | Backup is at the storage level |
| Differential backups | `BACKUP DATABASE ... WITH DIFFERENTIAL` | N/A | |
| Database snapshots | `BACKUP DATABASE ... WITH COPY_ONLY` | RDS console or API | Terminology differs; Aurora snapshots ≈ SQL Server `COPY_ONLY` backup |
| Database clones | `CREATE DATABASE ... AS SNAPSHOT OF...` | Database cloning | SQL Server database snapshot ≈ Aurora database cloning |
| Point-in-time restore | `RESTORE DATABASE \| LOG ... WITH STOPAT...` | Any point within retention via RDS console/API | |
| Partial restore | `RESTORE DATABASE... FILE=... \| FILEGROUP=...` | N/A | |
| Export/import table data | DTS, SSIS, BCP, linked servers | `SELECT INTO ... OUTFILE S3` / `LOAD DATA FROM S3` | |

- Aurora MySQL manages storage-level backups; transaction logs, filegroups, and backup
  purging are not applicable. Cluster volume max size is 64 TiB.
