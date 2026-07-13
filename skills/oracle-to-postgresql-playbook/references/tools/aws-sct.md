# AWS Schema Conversion Tool (AWS SCT)

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tools.awssct.html

**Conversion category:** N/A (migration tooling page)
**SCT automation:** This is the SCT tool itself. SCT automatically migrates most schema objects; objects it cannot convert are flagged with action codes (see sct-action-code-index.md) for manual handling.

## Oracle
AWS SCT is a Java utility that connects to the source Oracle database, scans schema objects (tables, views, indexes, procedures, etc.), and converts them to target objects. It greatly reduces manual effort because it migrates most database objects automatically.

Recommended workflow: start every migration with SCT, then use the rest of the playbook to manually solve objects that could not be converted automatically.

This walkthrough uses the AWS DMS Sample Database (downloadable from GitHub: https://github.com/aws-samples/aws-database-migration-samples).

## PostgreSQL
SCT generates the equivalent Aurora PostgreSQL DDL/code. End-to-end procedure:

**1. Download software and drivers**
- Install AWS SCT (from the AWS SCT user guide).
- Download the Oracle JDBC driver and the PostgreSQL JDBC driver.

**2. Configure AWS SCT**
1. Start AWS SCT.
2. Choose **Settings → Global settings**.
3. In the left nav, choose **Drivers**.
4. Enter the paths for the Oracle and PostgreSQL drivers.
5. Choose **Apply**, then **OK**.

**3. Create a new migration project**
1. Choose **File → New project wizard** (or `Ctrl+W`).
2. Enter a project name and location. Choose **Next**.
3. Enter source Oracle connection details, choose **Test connection**, then **Next**.
4. Select the schema/database to migrate, choose **Next**.
5. SCT analyzes objects and shows the **database migration assessment report**. Use **Save to PDF** for the full report including individual issue detail.
   - Review the **Database objects with conversion actions for Amazon Aurora (PostgreSQL compatible)** section (conversion statistics).
   - Review the **Detailed recommendations for Amazon Aurora (PostgreSQL compatible) migrations** section.
6. Choose **Next**, enter target Aurora PostgreSQL connection details, choose **Finish**.

**4. Explore issues and convert**
- The main window shows issues/recommendations. Objects with a red marker (e.g., issue 811 on `generate_tickets`) could not be auto-converted and need manual code changes.
- Right-click the schema → **Create report** for a target-tailored assessment report (executive summary + **Action items** tab to drill into each issue).
- Right-click the database → **Convert schema**. Uncheck the `sys` and `information_schema` system schemas (Aurora PostgreSQL already has `information_schema`). This step makes NO changes to the target.
- The right pane shows the new virtual schema as it would exist in the target; drilling into objects shows the actual generated migration syntax.
- Right-click the database (right pane) → either **Apply to database** (runs conversion script against the target) or **Save as SQL** (saves to a file).

## Conversion notes
- Recommended: **Save as SQL** rather than Apply, so you can verify/QA the converted code and hand-adjust objects that could not be converted automatically.
- Always uncheck `sys` and `information_schema` during conversion — Aurora PostgreSQL already provides `information_schema`.
- The **Convert schema** step is non-destructive; it only builds a virtual target schema until you explicitly Apply or run the saved SQL.
- Use SCT as the automated first pass, then consult the playbook's feature topics for the items SCT marks with action codes.
- See the AWS SCT User Guide for the full list of supported drivers and installation steps.
