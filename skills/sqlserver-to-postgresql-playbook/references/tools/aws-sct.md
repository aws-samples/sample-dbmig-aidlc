# AWS Schema Conversion Tool (AWS SCT) overview

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tools.awssct.html

**Conversion category:** N/A (tooling)
**SCT automation:** This page *is* the SCT walkthrough. SCT auto-converts most schema objects; objects it can't convert are flagged with action codes (see sct-action-code-index.md).

## SQL Server
- AWS SCT is a Java utility that connects to source and target databases, scans source schema objects (tables, views, indexes, procedures, etc.), and converts them to target objects.
- Acts as the **source connector** for the migration project; SQL Server is selected as the **Source engine**.
- Requires the **Microsoft SQL Server JDBC driver** (download separately; configure path in Global settings → Drivers).
- Recommended starting point for every migration: run SCT first, then use the Playbook to handle objects that couldn't be migrated automatically.

## PostgreSQL
- Aurora PostgreSQL is the **target engine**. Requires the **PostgreSQL JDBC driver** (download from jdbc.postgresql.org; configure path in Global settings → Drivers).
- SCT produces a **virtual schema** on the target side showing objects as if they existed in the target; drilling into an object shows the actual generated DDL/syntax.
- Note: Aurora PostgreSQL already has an `information_schema` schema. When converting, **uncheck the `sys` and `information_schema` system schemas**.

## Conversion notes
- **Download/install:** Get AWS SCT from the Schema Conversion Tool user guide; download SQL Server + PostgreSQL JDBC drivers.
- **Configure drivers:** Settings → Global settings → Drivers → enter SQL Server and PostgreSQL driver paths → Apply → OK.
- **New project:** File → New project wizard (Ctrl+W). Name + location. Source engine = Microsoft SQL Server → Next.
- **Connect source:** Enter SQL Server connection details → Test connection → Next. Select schema/database → Next.
- **Assessment report:** SCT analyzes objects and shows a database migration assessment report. Read the Executive summary; use **Save to PDF** for the full report including individual issue details. Key sections: "Database objects with conversion actions for Amazon Aurora (PostgreSQL compatible)" and "Detailed recommendations for Amazon Aurora (PostgreSQL compatible) migrations."
- **Connect target:** Next → enter Aurora PostgreSQL connection details → Finish.
- **Create report:** Right-click schema → Create report (tailored to target). Choose **Action items** to investigate each issue, drill down to all instances.
- **Convert schema:** Right-click database → Convert schema (uncheck `sys` and `information_schema`). This step makes **no changes** to the target database — it only builds the virtual schema.
- **Apply:** Right-click target database → either **Apply to database** (runs conversion script against target automatically) or **Save as SQL** (save to file).
- **Recommendation:** Prefer **Save as SQL** so you can verify/QA the converted code and adjust objects that couldn't be auto-converted.
- Walkthrough uses the AWS DMS Sample Database (available on GitHub: aws-samples/aws-database-migration-samples).
