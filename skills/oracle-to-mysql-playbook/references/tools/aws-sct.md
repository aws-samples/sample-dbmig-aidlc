# AWS Schema Conversion Tool (AWS SCT)

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.tools.awssct.html

**Conversion category:** N/A (migration tool)
**SCT automation:** This tool *is* AWS SCT. It automatically converts most database objects; remaining objects need manual conversion guided by the rest of the playbook.

## Overview

AWS SCT is a Java utility that connects to source and target databases, scans the source schema objects (tables, views, indexes, procedures, and so on), and converts them to target database objects. Because it can automatically migrate most database objects, it greatly reduces manual effort.

Recommended approach: start every migration with AWS SCT, then use the rest of the playbook to explore manual solutions for objects that couldn't be migrated automatically. The walkthrough uses the AWS DMS Sample Database (available on GitHub: https://github.com/aws-samples/aws-database-migration-samples).

## Download the software and drivers

1. Download and install AWS SCT. See "Installing, verifying, and updating" in the AWS SCT User Guide.
2. Download the Oracle and MySQL JDBC drivers. See "Installing the required database drivers".

## Configure AWS SCT

1. Start AWS SCT.
2. Choose **Settings** → **Global settings**.
3. On the left navigation bar, choose **Drivers**.
4. Enter the paths for the Oracle and MySQL drivers downloaded earlier.
5. Choose **Apply** then **OK**.

## Create a new migration project

1. Choose **File** → **New project wizard** (or **Ctrl+W**).
2. Enter a project name and location. For **Source engine**, choose **Oracle**, then **Next**.
3. Enter connection details for the source Oracle database, choose **Test connection** to verify, then **Next**.
4. Select the schema or database to migrate, then **Next**.
5. A progress bar shows objects being analyzed. When complete, AWS SCT displays the database migration assessment report. Read the Executive summary and other sections. The on-screen view is only partial — choose **Save to PDF** (top right) to read the full report including individual issue details.
6. Scroll to the **Database objects with conversion actions for Amazon Aurora (MySQL compatible)** section.
7. Scroll further to **Detailed recommendations for Amazon Aurora (MySQL compatible) migrations** and review.
8. Return to AWS SCT, choose **Next**, enter target Aurora MySQL connection details, and choose **Finish**.
9. After connecting, AWS SCT displays the main window where you can explore individual issues and recommendations.
10. Choose the schema → right-click → **Create report** to create a report tailored to the target. View it in AWS SCT.
11. The progress bar updates while the report is generated.
12. AWS SCT displays the executive summary page of the assessment report.
13. Choose **Action items** to investigate each issue in detail and view the suggested course of action; drill down to see all instances of each issue.
14. Choose the database → right-click → **Convert schema**. Uncheck the `sys` and `information_schema` system schemas. This step does NOT change the target database.
15. The right pane shows the new virtual schema as if it existed in the target. Drilling into objects shows the actual syntax AWS SCT generated.
16. Choose the database in the right pane → right-click → **Apply to database** (runs the conversion script against the target automatically) OR **Save as SQL** (saves to an SQL file).
17. Recommended: **Save as SQL** so you can verify and QA the converted code and adjust objects that couldn't be automatically converted.

## Conversion notes

- AWS SCT does NOT modify the target during analysis/convert-schema; only "Apply to database" or running the saved SQL changes the target.
- Saving to SQL (rather than auto-applying) is recommended so you can QA and manually fix objects that didn't convert.
- Always exclude `sys` and `information_schema` system schemas during conversion.
- The assessment report's on-screen content is partial — export to PDF for full issue detail.
- For per-feature automation levels and action codes, see the SCT action code index (sct-action-code-index.md).
