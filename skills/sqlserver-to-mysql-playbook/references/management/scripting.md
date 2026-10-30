# Scripting features

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.management.scripting.html

**Conversion category:** Manual (No feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): MySQL Shell added and MySQL Utilities marked discontinued, current server banner, 8.4 TLS/auth connection (verified), Data API, GO/DELIMITER note.

## SQL Server

SQL Server supports T-SQL and XQuery scripting within frameworks such as SQL Server Agent and stored procedures. The `SQLCMD` command-line utility runs T-SQL scripts, but the most feature-rich scripting environment is **PowerShell**.

SQL Server provides two PowerShell snap-ins exposing the entire SQL Server Management Object Model (SMO) as PowerShell paths. `Invoke-Sqlcmd` runs scripts via the SQLCMD utility. The `sqlps` utility launches PowerShell with SQL Server modules loaded (from a command prompt or SSMS Object Explorer); it runs one-time commands and `.ps1` script files. SQL Server Agent supports running PowerShell scripts in job steps.

Three direct database engine query types: **T-SQL**, **XQuery**, and the **SQLCMD utility** (which also supports commands and variables). T-SQL and XQuery can be called from stored procedures, SSMS/IDEs, and Agent jobs.

Examples:

```powershell
# Backup a database with default options
PS C:\> Backup-SqlDatabase -ServerInstance "MyServer\SQLServerInstance" -Database "MyDB"

# Read all rows from a table
PS C:\> Read-SqlTableData -ServerInstance "MyServer\SQLServerInstance" -DatabaseName "MyDB" -TableName "MyTable"
```

## MySQL

As a PaaS, Aurora MySQL accepts connections from any compatible client, but you can't access the MySQL command-line utility typically used for server administration. Use MySQL tools installed on a network host plus the Amazon RDS API. Common tools:

### MySQL Workbench
The most common MySQL development/admin tool (free Community + paid Commercial editions). Integrated IDE features:
* **SQL Development** — manage connections to Aurora MySQL clusters and run queries.
* **Data Modeling** — reverse/forward engineer schema models; manage schemas with the Table Editor.
* **Server Administration** — not applicable to Aurora MySQL (use the RDS console).

Also supports a Python scripting shell (interactive and programmatic).

### MySQL Shell
*(added)* MySQL Shell (`mysqlsh`, JavaScript/Python/SQL modes) is the current administration and scripting tool: parallel dump/load (`util.dumpSchemas`, `util.loadDump`), table import, upgrade checker (`util.checkForServerUpgrade` before 3 → 8.4). Use the 8.4 client for Aurora MySQL 8.4.

### MySQL Utilities
*(discontinued)* MySQL Utilities are no longer maintained; most functions moved to MySQL Shell. The list below is historical.
A set of Python command-line tools for maintenance/administration (some won't work on Aurora MySQL due to lack of root access):
* **Admin** — Clone, Copy, Compare, Diff, Export, Import, User Management.
* **Replication** — Setup, Configuration, Verification.
* **General** — Disk Usage, Redundant Indexes, Manage Metadata, Manage Audit Data.

### Amazon RDS API
A web service for managing relational databases (setup, operate, scale, backup, administer) across multiple platforms. Asynchronous — some interfaces require polling or callbacks. Accessed via:
* **AWS Management Console** — web-based interactive management (sign in → **RDS**).
* **AWS CLI** — open source, runs on Linux/Windows/macOS (Python 2 ≥ 2.6.5 or Python 3 ≥ 3.3); built on the AWS SDK for Python (Boto). Usable from Bash/Zsh/tsch, PowerShell/Windows Command Processor, or remotely via SSH/PuTTY. AWS Tools for PowerShell provide AWS resource scripting (but SQL Server cmdlets can't be used).
* **Amazon RDS Programmatic API** — automate management of DB instances and other RDS objects.

### Example (connect via the MySQL utility)
1. AWS console → **RDS** → **Databases**.
2. Choose the MySQL database and copy the cluster endpoint address.
3. In a shell:
   ```
   mysql -h <mysql-instance-endpoint-address> -P 3306 -u MasterUser
   ```
   (`-h` = endpoint DNS name, `-P` = port number.)
4. Provide the password when prompted:
   ```
   Welcome to the MySQL monitor. Commands end with ; or \g.
   Your MySQL connection id is 350
   Server version: 8.4.8 (Aurora MySQL 8.4)   -- the original showed a 5.6 server
   mysql>
   ```

## Conversion notes
- Non-compatible tool sets and scripting languages. AWS replacements: **MySQL Workbench**, **Amazon RDS API**, **AWS Management Console**, and **AWS CLI**.
- PowerShell SMO snap-ins / SQLCMD / `sqlps` have no equivalent; SQL Server cmdlets can't be used in AWS Tools for PowerShell.
- No direct host/CLI access to the server (PaaS) — administer via the RDS console/API/CLI; connect with a MySQL client over the cluster endpoint.
- Some MySQL Utilities require root access and won't work on Aurora MySQL; prefer MySQL Shell.
- Aurora MySQL 8.4 requires TLS (`require_secure_transport` = ON) and creates users with `caching_sha2_password` (verified): connect with `mysql --ssl-mode=VERIFY_IDENTITY --ssl-ca=global-bundle.pem …` and an 8.x client.
- The **RDS Data API** (`aws rds-data execute-statement`) runs SQL over HTTPS with IAM, without a network path to the cluster — useful for automation (used for all validation in this review).
- `sqlcmd` scripts with `GO` batch separators → the `mysql` client uses `;` and `DELIMITER //` for routine bodies; this toolkit applies DDL through PyMySQL without client delimiters.
