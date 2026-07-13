# Migrating ANSI SQL Features

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.sql.html

**Conversion category:** N/A (chapter overview)
**SCT automation:** N/A

## SQL Server

This chapter provides reference information for ANSI SQL operations required to migrate
from Microsoft SQL Server 2019 to Amazon Aurora MySQL. It covers key differences and
similarities in object name case sensitivity, constraint compatibility, table creation,
Common Table Expressions (CTEs), data type compatibility, GROUP BY operations, table
joins, views, window functions, and temporary tables.

## MySQL

Aurora MySQL-Compatible Edition is the migration target. Each topic below documents the
SQL Server feature, the Aurora MySQL equivalent or workaround, and migration notes.

## Conversion notes

Topics in this chapter:
- [Case sensitivity differences for ANSI SQL](case-sensitivity.md)
- [Constraints for ANSI SQL](constraints.md)
- [Creating tables for ANSI SQL](creating-tables.md)
- [Common table expressions for ANSI SQL](cte.md)
- [Data types for ANSI SQL](data-types.md)
- [GROUP BY for ANSI SQL](group-by.md)
- [Table JOIN for ANSI SQL](table-join.md)
- [Views for ANSI SQL](views.md)
- [Window functions for ANSI SQL](window-functions.md)
- [Temporary tables for ANSI SQL](temporary-tables.md)
