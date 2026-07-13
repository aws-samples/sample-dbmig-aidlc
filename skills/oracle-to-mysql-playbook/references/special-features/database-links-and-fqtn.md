# Oracle Database Links and MySQL Fully-Qualified Table Names

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.dblinks.html

**Conversion category:** Manual (two-star feature compatibility) — MySQL does not support database links.
**SCT automation:** N/A

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
