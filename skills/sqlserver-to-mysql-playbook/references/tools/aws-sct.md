# AWS Schema Conversion Tool (AWS SCT) Overview

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.tools.awssct.html

**Conversion category:** N/A (tooling)
**SCT automation:** This is the SCT tool itself — it auto-converts most compatible objects and flags the rest with action codes.

## SQL Server
AWS SCT is a Java utility that connects to source and target databases, scans the source schema objects (tables, views, indexes, procedures, etc.) and converts them to target objects. For SQL Server sources, it connects via a JDBC driver (Microsoft SQL Server JDBC driver) you download and configure.

Recommended workflow: start every migration with SCT, then use the rest of the playbook to explore manual solutions for objects that couldn't be migrated automatically. The walkthrough uses the AWS DMS Sample Database (available on GitHub).

## MySQL
The Aurora MySQL (MySQL-compatible) side requires the MySQL JDBC driver (Connector/J) to be downloaded and configured in SCT. SCT generates a virtual target schema, produces the converted DDL, and can either apply it directly to the Aurora MySQL target or export it to a SQL file.

## Conversion notes
- **Download software and drivers:** Install AWS SCT; download Microsoft SQL Server and MySQL JDBC drivers.
- **Configure SCT:** Start SCT → **Settings** → **Global settings** → **Drivers** → enter paths for the SQL Server and MySQL drivers → **Apply** → **OK**.
- **New project:** **File** → **New project wizard** (Ctrl+W). Name the project, choose **Microsoft SQL Server** as source engine.
- **Connect source:** enter SQL Server connection details, **Test connection**, **Next**; select schema/database to migrate.
- **Assessment report:** SCT analyzes objects and displays a database migration assessment report. Read the Executive summary; **Save to PDF** for the full report. Review **Database objects with conversion actions for Amazon Aurora (MySQL compatible)** and **Detailed recommendations** sections.
- **Connect target:** enter Aurora MySQL connection details, **Finish**.
- **Create report:** right-click schema → **Create report** for a target-tailored assessment; review **Action items** with suggested courses of action, drilling into each instance.
- **Convert schema:** right-click database → **Convert schema**. Uncheck `sys` and `information_schema` system schemas. This makes no changes to the target — it builds a virtual target schema on the right pane; drill into objects to see generated syntax.
- **Apply:** right-click target database → **Apply to database** (runs conversion script against target) **or** **Save as SQL** (export to file).
- **Recommendation:** Save to SQL file so you can verify/QA the converted code and adjust objects that couldn't be auto-converted.
