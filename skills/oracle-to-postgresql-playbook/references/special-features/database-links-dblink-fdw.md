# Database Links — dblink and Foreign Data Wrapper (FDW)

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.dblinks.html

**Conversion category:** Manual (Three-star feature compatibility, no automation)
**SCT automation:** No automation. SCT action code index: Database Links. Key differences: different paradigm and syntax.

## Oracle

Database links are schema objects to interact with remote database objects (e.g. tables). Oracle Net Services must be installed on both local and remote servers.

Create database links (via TNS entry or full TNS connection string):
```sql
CREATE DATABASE LINK remote_db CONNECT TO username IDENTIFIED BY password USING 'remote';

CREATE DATABASE LINK remotenoTNS CONNECT TO username IDENTIFIED BY password
  USING '(DESCRIPTION=(ADDRESS_LIST=(ADDRESS = (PROTOCOL = TCP)(HOST =192.168.1.1)
  (PORT =1521)))(CONNECT_DATA =(SERVICE_NAME = orcl)))';
```

Use the link as an `@remote_db` suffix on the table name:
```sql
SELECT * FROM employees@remote_db;
```

DML is supported:
```sql
INSERT INTO employees@remote_db
(employee_id, last_name, email, hire_date, job_id) VALUES
(999, 'Claus', 'sclaus@example.com', SYSDATE, 'SH_CLERK');

UPDATE jobs@remote_db SET min_salary = 3000 WHERE job_id = 'SH_CLERK';

DELETE FROM employees@remote_db WHERE employee_id = 999;
```

Drop a link: `drop database link remote;`

## PostgreSQL

Two options for querying remote databases:
1. **`dblink`** function.
2. **`postgres_fdw`** (Foreign Data Wrapper) extension — newer, aligns closer to SQL standard, often better performance.

**Using dblink:**
```sql
CREATE EXTENSION dblink;

-- persistent named connection
SELECT dblink_connect
('myconn', 'dbname=postgres port=5432 host=hostname user=username password=password');

-- query via named connection (must declare returned columns + types)
SELECT * from dblink
('myconn', 'SELECT id, name FROM EMPLOYEES')
AS p(id int,fullname text);

SELECT dblink_disconnect('myconn');
```

Alternatively use a full connection string inline:
```sql
SELECT * from dblink
('dbname=postgres port=5432 host=hostname user=username password=password',
'SELECT id, name FROM EMPLOYEES') AS p(id int,fullname text);
```

DML over dblink:
```sql
SELECT * FROM dblink('myconn',$$INSERT into employees
VALUES (3,'New Employees No.3!')$$) AS t(message text);

SELECT * FROM dblink('myconn',$$DELETE FROM employees WHERE id=3$$) AS t(message text);
```

Create a local table from remote data; join remote with local; run remote DDL:
```sql
SELECT emps.* INTO new_employees_table
FROM dblink('myconn','SELECT * FROM employees') AS emps(id int, name varchar);

SELECT local_emps.id , local_emps.name, s.sale_year, s.sale_amount
FROM local_emps INNER JOIN
dblink('myconn','SELECT * FROM working_hours') AS s(id int, hours worked int)
ON local_emps.id = s.id;

SELECT * FROM dblink('myconn',$$CREATE table new_remote_tbl (a int, b text)$$) AS t(a text);
```

**Using postgres_fdw:**
```sql
CREATE EXTENSION postgres_fdw;

CREATE SERVER remote_db
FOREIGN DATA WRAPPER postgres_fdw
OPTIONS (host 'hostname', dbname 'postgresql', port '5432');

CREATE USER MAPPING FOR local_user
SERVER remote_db
OPTIONS (user 'remote_user', password 'remote_password');

CREATE FOREIGN TABLE foreign_emp_tbl (
  id int, name text)
  SERVER remote_db
  OPTIONS (schema_name 'hr', table_name 'employees');

SELECT * FROM foreign_emp_tbl;

-- import a whole schema (or specific tables)
IMPORT FOREIGN SCHEMA hr LIMIT TO (employees)
FROM SERVER remote_db INTO local_hr;
```

### dblink vs Foreign Data Wrapper

| Description | dblink | Foreign Data Wrapper |
|---|---|---|
| Permanent reference to a remote table | Not supported | Supported via `CREATE FOREIGN TABLE ... SERVER ... OPTIONS (schema_name, table_name)` |
| Query remote data | `SELECT * FROM dblink('myconn','SELECT * FROM employees') AS p(id int,fullname text, address text);` | `SELECT * FROM foreign_emp_tbl;` |
| DML on remote data | `SELECT * FROM dblink('myconn',$$INSERT into employees VALUES (45,'Dan','South side 7432, NY')$$) AS t(id int, name text, address text);` | Regular DML: `INSERT into foreign_emp_tb VALUES (45,'Dan','South side 7432, NY');` |
| Run DDL on remote objects | `SELECT * FROM dblink('myconn',$$CREATE table my_remote_tbl (a int, b text)$$) AS t(a text);` | Not supported |

## Conversion notes
- No automation; requires manual rewrite due to different paradigm and syntax.
- PostgreSQL has **no permanent named database link** like Oracle. With dblink you open a connection per session/query; with FDW you define a server + user mapping + foreign table.
- **Heterogeneous links** (Oracle↔PostgreSQL): Oracle supports them; `oracle_fdw` is **not supported by Amazon RDS**.
- Both dblink and FDW store remote credentials as **plain text** (in `pg_user_mapping`, viewable only by superusers; dblink passwords may also live in code/procedures). Changing a PostgreSQL user password requires updating the FDW/dblink specs.
- FDW queries **fail if remote columns are dropped/renamed** — the foreign tables must be re-created.
- Oracle cannot run DDL directly over a link, but can submit a remote job (e.g. `dbms_job@remote.submit(...)`) to run DDL.
- "Delete a database link": Oracle `drop database link`; PostgreSQL dblink has no equivalent — close the connection with `SELECT dblink_disconnect('myconn');`.
