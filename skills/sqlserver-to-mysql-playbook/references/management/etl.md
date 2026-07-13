# ETL features

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.management.etl.html

**Conversion category:** Manual (One star feature compatibility)
**SCT automation:** N/A

## SQL Server

SQL Server offers a native ETL framework. The legacy **Data Transformation Services (DTS)** was deprecated as of SQL Server 2008 and replaced with **SQL Server Integration Services (SSIS)** (introduced in 2005).

**DTS** (SQL Server 7/2000): supported OLE DB, ODBC, and text-file drivers; transformations schedulable via SQL Server Agent; version control via tools like Visual SourceSafe. The fundamental entity was the DTS Package (logical container for connections, data transfers, transformations, notifications). Tools: DTS Wizards, DTS Package Designers, DTS Query Designer, DTS Run Utility.

**SSIS** (SQL Server 2005+, top-tier editions): a modern, enterprise-class heterogeneous platform for data migration and processing with workflow-oriented design. Tools:
* SSIS Import/Export Wizard (SSMS extension; limited transformations).
* SQL Server Business Intelligence Development Studio (BIDS), now replaced by SQL Server Data Tools — Business Intelligence (SSDT-BI).

SSIS objects: connections, event handlers, workflows, error handlers, parameters (2012+), precedence constraints, tasks, variables. Packages are XML documents saved to the file system or stored in a SQL Server instance.

## MySQL

Aurora MySQL uses **AWS Glue** for enterprise ETL — a fully managed service for cataloging, cleansing, enriching, and moving data between heterogeneous sources/destinations (no infrastructure to manage). Key features:

* **Integrated Data Catalog** — persistent metadata store (cloud or on-prem); stores table schemas, job steps, statistics, partitions, and schema version history.
* **Automatic Schema Discovery** — crawlers connect to sources/targets, use classifiers to infer schema, and store metadata in the catalog; scheduled, on-demand, or event-triggered.
* **Code Generation** — auto-generates ETL code (Scala or Python for Apache Spark); point Glue at source and target.
* **Developer Endpoints** — for interactive editing/debugging/testing with any IDE; custom libraries and shared code (AWS Glue GitHub repo).
* **Flexible Job Scheduler** — schedule, on-demand, or event-triggered; parallel jobs, explicit inter-job dependencies, bad-data filtering, retries; logs/notifications to CloudWatch.

### Migration Considerations

There are **no automatic tools** to migrate DTS/SSIS packages into AWS Glue — ETL processes must be rewritten. Alternatively, run an EC2 SQL Server instance hosting SSIS as an interim solution (revise connectors/tasks to target Aurora MySQL), allowing gradual migration to Glue.

### Example (CSV from S3 → Aurora MySQL via Glue)

1. **Create an S3 bucket and upload the CSV** — choose **S3** → **Create bucket** (name, region, access, versioning/encryption), then **Upload** → **Add files** → select CSV → **Upload**.
2. **Add a Glue crawler** — **AWS Glue** → **Tables** → **Add tables using a crawler**; name it; specify the S3 path data store; choose/create an IAM role; **Run on demand**; choose an output database and optional table prefix; **Finish**.
3. **Run the crawler** — **AWS Glue** → **Crawlers** → select → **Run crawler**. After completion, verify the discovered table's properties and schema (adjust manually if needed). Tables can also be added manually via **Add table manually**.
4. **Create an ETL job** — **AWS Glue** → **Jobs (legacy)** → **Add job**; name it and pick the IAM role; choose script source (Glue-generated); select the data source; transform type **Change schema**; data target **Create tables in your data target** using JDBC `gluerds` connection (**Add connection** with Aurora instance details); review column mapping; **Save job and edit script**; review/edit generated script; **Run job**. Verify status **Succeeded** on the history tab and query the Aurora MySQL cluster to confirm.

## Conversion notes
- AWS service replacement: SSIS/DTS → **AWS Glue** (serverless Spark-based ETL; scripts in Python or Scala).
- No automated DTS/SSIS → Glue migration; ETL logic must be re-authored.
- Interim option: host SSIS on an EC2 SQL Server instance, re-pointing connectors/tasks to Aurora MySQL, then migrate incrementally to Glue.
- Glue integrates with the Data Catalog, crawlers, CloudWatch logging/alerts, and IAM roles for security.
