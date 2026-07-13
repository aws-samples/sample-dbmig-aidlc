# DBMS_REDEFINITION

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.redefinition.html

**Conversion category:** Manual (★★ feature compatibility, no automation)
**SCT automation:** N/A — MySQL doesn't support `DBMS_REDEFINITION`.

## Oracle

`DBMS_REDEFINITION` reorganizes tables online while DML continues — e.g., to reclaim space below the high watermark or change a table's DDL. Oracle uses materialized views to track changes on the master table and applies them during refresh synchronization.

Online redefinition subprograms:
* `CAN_REDEF_TABLE` — check if the table can be redefined.
* `START_REDEF_TABLE` — start online redefinition.
* `SYNC_INTERIM_TABLE` — sync the interim table with new data.
* `FINISH_REDEF_TABLE` — complete redefinition.

```sql
EXEC DBMS_REDEFINITION.CAN_REDEF_TABLE('HR', 'EMPLOYEES');
CREATE TABLE employees2 AS SELECT * FROM employees WHERE 1=2;

EXEC DBMS_REDEFINITION.START_REDEF_TABLE('HR','EMPLOYEES','EMPLOYEES2','*');
EXEC DBMS_REDEFINITION.SYNC_INTERIM_TABLE('HR','EMPLOYEES','EMPLOYEES2');

ALTER TABLE employees2 ADD
  (CONSTRAINT emp_pk2 PRIMARY KEY (empno) USING INDEX);

EXEC DBMS_REDEFINITION.FINISH_REDEF_TABLE('HR','EMPLOYEES','EMPLOYEES2');
DROP TABLE employees2;
```

## MySQL

No equivalent for automatic table rebuild or two-table sync. Workaround:
1. Copy data to a new table with `CREATE TABLE AS SELECT` or `mysqldump`.
2. Copy delta rows using **triggers** on the source table.
3. When the application is ready, sync and switch to the new table.

If a table has sequence (`AUTO_INCREMENT`) columns, the last sequence value is retained when the table is copied.

## Conversion notes
- No online-redefinition package — implement the copy + trigger-based delta + cutover pattern manually.
- For schema changes, MySQL's online DDL (`ALTER TABLE ... ALGORITHM=INPLACE, LOCK=NONE`) can cover many cases that Oracle used `DBMS_REDEFINITION` for — evaluate per change.
- Preserve `AUTO_INCREMENT` last value during the copy.
