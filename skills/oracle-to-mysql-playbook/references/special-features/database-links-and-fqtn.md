# Oracle Database Links and MySQL Fully-Qualified Table Names

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.dblinks.html

**Conversion category:** Manual (two-star feature compatibility) — MySQL does not support database links.
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): FEDERATED engine not available and silently substituted by InnoDB under the Aurora default sql_mode (verified on both versions); practical replacements.

## Oracle

Database links are schema objects used to access remote database objects (e.g., tables in a remote database). Oracle Net Services must be installed on both local and remote servers.

Create a database link (via TNS entry or full connection string):

```sql
CREATE DATABASE LINK remote_db CONNECT TO username IDENTIFIED BY password USING 'remote';

CREATE DATABASE LINK remotenoTNS CONNECT TO username IDENTIFIED BY password
  USING '(DESCRIPTION=(ADDRESS_LIST=(ADDRESS = (PROTOCOL = TCP)(HOST =192.168.1.1)
  (PORT =1521)))(CONNECT_DATA =(SERVICE_NAME = orcl)))';
```

Use the link with `@remote_db` suffix on a table name:

```sql
SELECT * FROM employees@remote_db;
```

Database links also support DML:

```sql
INSERT INTO employees@remote_db
(employee_id, last_name, email, hire_date, job_id) VALUES
(999, 'Claus', 'sclaus@example.com', SYSDATE, 'SH_CLERK');

UPDATE jobs@remote_db SET min_salary = 3000 WHERE job_id = 'SH_CLERK';

DELETE FROM employees@remote_db WHERE employee_id = 999;
```

## MySQL

MySQL has no direct equivalent to Oracle database links. If the data resides within the **same** MySQL cluster, you can use fully-qualified names (`database.table`), similar to cross-schema querying in Oracle:

```sql
SELECT flight_id FROM flights.all_flights;
```

The query returns data only if the user has permissions to the table and database. If the data cannot be co-located in the same MySQL cluster, there is no equivalent to Oracle database links.

## Conversion notes

- Cross-database access works only within a single cluster via fully-qualified `db.table` names.
- True cross-server/remote-database access (the core use case for Oracle DB links) has no MySQL equivalent — re-architect via the application layer, ETL (e.g., AWS Glue), or by consolidating data into one cluster.
- DML through a remote link (insert/update/delete on a remote table) cannot be reproduced and must move to application logic.
- The `FEDERATED` storage engine is **not available** on Aurora MySQL 3 or 8.4 (`information_schema.engines` reports `NO`, verified). `CREATE TABLE … ENGINE=FEDERATED` **silently creates an ordinary InnoDB table** — with the Aurora default `sql_mode` and even with `NO_ENGINE_SUBSTITUTION` set (verified on both versions). Check `information_schema.tables.ENGINE` after applying converted DDL.
- Practical replacements: consolidate the linked schemas into one Aurora cluster (cross-database `db.table` queries and joins work); replicate the remote tables into the cluster with AWS DMS or binlog replication; query across engines with Amazon Athena federated queries; or call a Lambda function (`lambda_sync`) for occasional remote lookups.
