# SQL Server Deprecated Features — SQL Server to Aurora MySQL

> Source: SQL Server 2018 deprecated features list — Microsoft SQL Server 2019 to Amazon Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.deprecatedfeatures.html

Reference list of SQL Server features deprecated as of SQL Server 2018/2019. When migrating
to Aurora MySQL, these constructs must be rewritten — most have no direct equivalent and
require the replacement noted below.

## SQL Server

| Deprecated SQL Server feature | Playbook section | Replacement / Aurora MySQL equivalent |
|---|---|---|
| `TEXT`, `NTEXT`, and `IMAGE` data types | Data Types | Use large-object types instead: in SQL Server `VARCHAR(MAX)` / `NVARCHAR(MAX)` / `VARBINARY(MAX)`. In Aurora MySQL map to `TEXT`/`LONGTEXT` (character data) and `BLOB`/`LONGBLOB` (binary data). |
| `SET ROWCOUNT` for DML (`INSERT`, `UPDATE`, `DELETE`) | Session Options | Use the `TOP` clause in SQL Server. In Aurora MySQL use the `LIMIT` clause on the DML statement to bound affected rows. |
| `TIMESTAMP` syntax for `CREATE TABLE` (the SQL Server row-version pseudo type) | Creating Tables | Use `ROWVERSION` in SQL Server. In Aurora MySQL emulate row versioning with a `TIMESTAMP`/`DATETIME` column using `DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`, or an application/trigger-maintained version counter. |
| `DBCC DBREINDEX`, `INDEXDEFRAG`, and `SHOWCONTIG` | Maintenance Plans | Use `ALTER INDEX ... REBUILD` / `REORGANIZE` and `sys.dm_db_index_physical_stats` in SQL Server. In Aurora MySQL use `OPTIMIZE TABLE` / `ALTER TABLE ... ENGINE=InnoDB` to rebuild, and `ANALYZE TABLE` to refresh statistics. |
| Old SQL Mail | Database Mail | Use Database Mail in SQL Server. Aurora MySQL has no built-in mail subsystem — send notifications from the application layer or via Amazon SNS / Amazon SES. |
| `IDENTITY` seed, increment, non–primary key, and compound identity usage | Identity and Sequences | Use `SEQUENCE` objects in SQL Server. In Aurora MySQL use `AUTO_INCREMENT` columns (one per table, must be indexed/key); for non-trivial sequence semantics emulate with a sequence table or application-generated keys. |
| Stored procedures `RETURN` values | Stored Procedures | Use `OUTPUT` parameters or a result set in SQL Server. In Aurora MySQL use `OUT`/`INOUT` procedure parameters or a returned result set (MySQL stored procedures do not return scalar status codes). |
| `GROUP BY ALL`, `CUBE`, and `COMPUTE BY` | GROUP BY | Use the standard `GROUP BY` with `GROUPING SETS` / `ROLLUP` / `CUBE` operators in SQL Server. In Aurora MySQL use `GROUP BY ... WITH ROLLUP`; compute subtotals/aggregates in the application or with additional queries (`COMPUTE BY` is unsupported). |
| DTS (Data Transformation Services) | ETL | Use SQL Server Integration Services (SSIS) in SQL Server. For Aurora MySQL use AWS DMS, AWS Glue, or other ETL tooling. |
| Old outer join syntax `*=` and `=*` | Table JOIN | Use ANSI join syntax `LEFT OUTER JOIN` / `RIGHT OUTER JOIN` with the `ON` clause. Aurora MySQL supports only the ANSI `JOIN ... ON` syntax. |
| `'String Alias' = Expression` (column alias assignment form) | Migration Quick Tips | Use `Expression AS Alias` (or `Expression Alias`). Aurora MySQL requires the standard `AS` alias syntax. |
| `DEFAULT` keyword for `INSERT` statements | Migration Quick Tips | Omit the column (let the column default apply) or supply an explicit value. Aurora MySQL supports `DEFAULT` in `INSERT`, but verify behavior matches the SQL Server column default during conversion. |

## Conversion notes

- These deprecated constructs frequently appear in T-SQL stored procedures, functions, and
  triggers — see the procedural/T-SQL conversion references under [`../tsql/`](../tsql/)
  (e.g. Identity and Sequences, Stored Procedures).
- Query-level rewrites (joins, `GROUP BY`, aliasing, `INSERT ... DEFAULT`) follow standard
  SQL conversion guidance — see the ANSI SQL references under
  [`../ansi-sql/`](../ansi-sql/).
- Prefer ANSI-standard SQL wherever a deprecated SQL Server extension is encountered; this
  maximizes portability to Aurora MySQL and reduces the conversion surface.
