# Scripting features

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.scripting.html

**Conversion category:** N/A (no feature compatibility)
**SCT automation:** N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): AWS CLI v2, TLS connection string, RDS Data API for scripting, IaC.

Key difference: Non-compatible tool sets and scripting languages. Use PostgreSQL `pgAdmin`, the Amazon RDS API, the AWS Management Console, and the AWS CLI.

## SQL Server

SQL Server supports T-SQL and XQuery scripting in multiple frameworks (SQL Server Agent, stored procedures). `SQLCMD` runs T-SQL scripts, but the richest environment is PowerShell.

- Two PowerShell snap-ins expose the SQL Server Management Object Model (SMO) as PowerShell paths.
- `Invoke-Sqlcmd` runs scripts through the SQLCMD utility.
- `sqlps` launches PowerShell with SQL Server modules auto-loaded (from a prompt or SSMS Object Explorer); runs one-time commands or `.ps1` files.
- SQL Server Agent can run PowerShell scripts in job steps.
- Three direct engine query types: T-SQL, XQuery, and the SQLCMD utility (callable from procedures, SSMS, and Agent jobs).

Examples:

```powershell
# Backup a database with default options
PS C:\> Backup-SqlDatabase -ServerInstance "MyServer\SQLServerInstance" -Database "MyDB"

# Read all rows from a table
PS C:\> Read-SqlTableData -ServerInstance "MyServer\SQLServerInstance" -DatabaseName "MyDB" -TableName "MyTable"
```

## PostgreSQL

As a PaaS, Aurora PostgreSQL accepts connections from any compatible client but you cannot access the server's command line for administration. Use PostgreSQL tools on a network host plus the Amazon RDS API. Common tools:

- **pgAdmin** — most common dev/admin tool for PostgreSQL; includes a Python scripting shell (interactive and programmatic). Free Community Edition.
- **Amazon RDS API** — web service to set up, operate, scale, back up, and administer Aurora PostgreSQL (and other engines); supports multiple platforms; asynchronous (may require polling/callbacks). Accessible via the AWS Management Console, AWS CLI, and the programmatic API.
- **AWS Management Console** — web-based interactive management (sign in → **RDS**).
- **AWS CLI v2** — runs on Linux/Windows/macOS as a self-contained installer (no system Python required). Usable from Bash/Zsh/tsch, PowerShell/Windows command processor, or remotely over SSH/PuTTY. AWS Tools for PowerShell expose AWS resources as cmdlets — but SQL Server cmdlets cannot be used in PowerShell.
- **Amazon RDS Programmatic API** — automate management of DB instances and other RDS objects.

Example — connect to an Aurora PostgreSQL instance with the `psql` utility:
1. Sign in → **RDS** → **Databases**.
2. Choose the database and copy the cluster endpoint address (you can also connect to individual instances).
3. Run:

   ```bash
   psql "host=mypostgresql.c6c8mwvfdgv0.us-west-2.rds.amazonaws.com port=5432 \
         user=awsuser dbname=mypgdb sslmode=verify-full sslrootcert=global-bundle.pem"
   ```
   Aurora PostgreSQL 18 requires TLS by default (`rds.force_ssl = 1`). Use PostgreSQL 18 client tools.

   `--host` is the cluster endpoint DNS name; `--port` is the port number.

## Conversion notes

- Non-compatible tooling — T-SQL/XQuery/PowerShell-SMO scripting has no direct equivalent; rewrite administration scripts using pgAdmin (Python shell), `psql`, the AWS CLI, or the Amazon RDS API/SDKs.
- AWS service replacements: AWS Management Console, AWS CLI, and Amazon RDS API/SDKs replace SMO/PowerShell-based DBA automation.
- SQL Server PowerShell cmdlets are not usable against Aurora PostgreSQL; the RDS API is asynchronous (plan for polling/callbacks).
- **RDS Data API** (`aws rds-data execute-statement`, enabled with `--enable-http-endpoint`) runs SQL over HTTPS with IAM auth and needs no network path to port 5432. It is a good fit for PowerShell/automation scripts (AWS Tools for PowerShell `Invoke-RDSDATAStatement`). This review used it to validate every PostgreSQL 18 claim.
- Infrastructure scripting (create clusters, parameter groups, snapshots) → AWS CloudFormation / CDK / Terraform rather than imperative scripts.
