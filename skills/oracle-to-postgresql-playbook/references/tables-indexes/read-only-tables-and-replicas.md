# Read-Only Tables/Partitions and Aurora Replicas

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.readonly.html

**Conversion category:** Manual (three-star feature compatibility)
**SCT automation:** No automation. N/A.

## Oracle
Beginning with Oracle 11g, tables can be marked read-only to block DML. Before 11g the only option was restricting privileges to `SELECT` (owner could still write).

- 11g: `ALTER TABLE ... READ ONLY` / `READ WRITE`.
- 12c R2: granular read-only **partitions/sub-partitions**; DML on a `READ ONLY` partition errors.
- `SELECT FOR UPDATE` not allowed on read-only tables.
- DDL allowed if it doesn't modify table data; index operations allowed.

```sql
CREATE TABLE EMP_READ_ONLY (
EMP_ID NUMBER PRIMARY KEY,
EMP_FULL_NAME VARCHAR2(60) NOT NULL);

INSERT INTO EMP_READ_ONLY VALUES(1, 'John Smith');   -- 1 row created

ALTER TABLE EMP_READ_ONLY READ ONLY;

INSERT INTO EMP_READ_ONLY VALUES(2, 'Steven King');
-- ORA-12081: update operation not allowed on table

ALTER TABLE EMP_READ_ONLY READ WRITE;
INSERT INTO EMP_READ_ONLY VALUES(2, 'Steven King');  -- 1 row created
COMMIT;
```

## PostgreSQL
PostgreSQL has **no** equivalent `READ ONLY` table mode. Workarounds:

**1. Read-only user/role** — grant only `SELECT` and set `default_transaction_read_only=ON`:

```sql
CREATE TABLE EMP_READ_ONLY (
  EMP_ID NUMERIC PRIMARY KEY,
  EMP_FULL_NAME VARCHAR(60) NOT NULL);

CREATE USER aws_readonly PASSWORD 'aws_readonly';
ALTER USER aws_readonly SET DEFAULT_TRANSACTION_READ_ONLY=ON;
GRANT SELECT ON EMP_READ_ONLY TO aws_readonly;

-- As aws_readonly:
INSERT INTO EMP_READ_ONLY VALUES(1, 'John Smith');
-- ERROR: cannot execute INSERT in a read-only transaction
```

**2. Read-only database** — dedicate a database with `DEFAULT_TRANSACTION_READ_ONLY=ON`:

```sql
CREATE DATABASE readonly_db;
ALTER DATABASE readonly_db SET DEFAULT_TRANSACTION_READ_ONLY=ON;
-- connected to readonly_db:
INSERT INTO EMP_READ_ONLY VALUES(1, 'John Smith');
-- ERROR: cannot execute INSERT in a read-only transaction
```
Set the parameter to `OFF` to allow writes again.

**3. Read-only trigger** — block DML/TRUNCATE via a trigger:

```sql
CREATE OR REPLACE FUNCTION READONLY_TRIGGER_FUNCTION()
  RETURNS TRIGGER AS $$
  BEGIN
    RAISE EXCEPTION 'THE "%" TABLE IS READ ONLY!', TG_TABLE_NAME
      using hint = 'Operation Ignored';
    RETURN NULL;
  END;
$$ language 'plpgsql';

CREATE TRIGGER EMP_READONLY_TRIGGER
  BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE
  ON EMP_READ_ONLY FOR EACH STATEMENT
  EXECUTE PROCEDURE READONLY_TRIGGER_FUNCTION();
```

## Conversion notes
- No native read-only table/partition setting in PostgreSQL — choose user/role, database, or trigger workaround based on granularity needed.
- Role/database approaches are coarse-grained (per-session/per-database); the trigger approach gives per-table control and a clear error message.
- For minimal-downtime migration, Oracle read-only tables/partitions support ongoing replication from source, while Aurora PostgreSQL **read replicas** provide read scaling on the target.
