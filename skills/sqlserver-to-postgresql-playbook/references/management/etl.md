# ETL features

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.etl.html

**Conversion category:** N/A (no feature compatibility)
**SCT automation:** N/A

Key difference: Use AWS Glue for ETL.

## SQL Server

SQL Server offers a native ETL framework. The legacy Data Transformation Services (DTS, introduced in v7, expanded in 2000) was deprecated in SQL Server 2008 and replaced by SQL Server Integration Services (SSIS, introduced in 2005).

- **DTS**: visual ETL across heterogeneous sources/targets; supported OLE DB, ODBC, text drivers; scheduled via SQL Server Agent; the DTS Package was the core container. Tools: DTS Wizards, Package Designers, Query Designer, Run Utility.
- **SSIS**: modern enterprise heterogeneous platform; workflow-oriented design, data-warehousing features, scheduling for multidimensional cubes. Tools: Import/Export Wizard (SSMS extension), BIDS / SSDT-BI for complex packages. SSIS objects: Connections, Event handlers, Workflows, Error handlers, Parameters (2012+), Precedence constraints, Tasks, Variables. Packages are XML documents stored on the file system or inside SQL Server.

## PostgreSQL

Aurora PostgreSQL uses **AWS Glue** — a fully managed ETL service for cataloging, cleansing, enriching, and moving data between heterogeneous sources/destinations (no infrastructure to manage).

Key features:
- **Integrated data catalog** — persistent metadata store (table schemas, job steps), partition registration, schema version history.
- **Automatic schema discovery** — crawlers connect to sources/targets, classify data, and populate the Data Catalog (scheduled, on-demand, or event-triggered).
- **Code generation** — auto-generates Scala or Python (Apache Spark) ETL scripts from source→target.
- **Developer endpoints** — interactive editing/debugging/testing in any IDE; custom libraries; shared code via the AWS Glue GitHub repo.
- **Flexible job scheduler** — schedule, on-demand, or event-driven; parallel jobs with dependencies; retries; logs/notifications to Amazon CloudWatch.

Migration: Use AWS SCT to convert SSIS ETL scripts to AWS Glue (see SCT "Converting SSIS").

Example — AWS Glue job to load a CSV (Visits table) from Amazon S3 into Aurora PostgreSQL:

1. **Create an S3 bucket and upload the CSV**: S3 → Create bucket (unique name, region, access level, versioning/encryption) → upload the CSV file.
2. **Add a Glue crawler** to discover/catalog the file: Glue → Tables → Add tables using a crawler → name it → keep default source type → specify the S3 path → choose/create an IAM role → schedule "Run on demand" → choose output database and optional table prefix → Finish.
3. **Run the crawler**: Glue → Crawlers → select → Run crawler. After completion the table is recorded in the catalog; verify properties/schema (adjustable via JSON). Tables can also be added manually (Glue → Tables → Add table manually).
4. **Create an ETL job** to copy Visits to Aurora PostgreSQL: Glue → Jobs (legacy) → Add job → name + IAM role → choose script source (use Glue-generated) → select data source → transform type **Change schema** → data target **Create tables in your data target** using JDBC store and `gluerds` connection → Add Connection (Aurora instance access details) → review column mapping → Save job and edit script → optionally edit the generated script → Run job. Verify status **Succeeded** under the history tab and query the target to confirm the data transferred.

## Conversion notes

- No compatible ETL engine — replace SSIS/DTS packages with AWS Glue jobs.
- AWS service replacements: AWS Glue (ETL + Data Catalog + crawlers), Amazon S3 (staging), Amazon CloudWatch (logs/alerts).
- AWS SCT can automate conversion of existing SSIS packages to AWS Glue.
- Glue generates Python/Scala Spark scripts; expect to review/tune generated code and column mappings.
