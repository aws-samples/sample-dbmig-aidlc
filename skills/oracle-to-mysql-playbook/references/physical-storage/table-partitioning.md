# Oracle and MySQL Table Partitioning

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.storage.partition.html

**Conversion category:** Assisted (three-star feature compatibility; three-star SCT automation)
**SCT automation:** Partitioning action code index. Aurora MySQL does **not** support interval partitioning, partition advisor, preference partitioning, virtual column-based partitioning, or automatic list partitioning.

Table partitioning divides a large table into smaller pieces. Each partition has its own name and definition and can be managed separately or collectively. Partitioning is transparent to applications (unmodified SQL still works) and improves query performance, eases data management/ILM, and reduces maintenance downtime.

## Oracle

Oracle benefits: performance (scan a partition subset, parallel DML/DDL), data management (migration, index ops, backup/recovery), and reduced maintenance downtime. Oracle 18c added online partition/subpartition merging and online partitioning-strategy changes (e.g. hash → range). Oracle 19c added hybrid partitioned tables (mixing internal and external partitions).

### Hash partitioning

Oracle applies a hashing algorithm to a partition key to evenly distribute rows across partitions of approximately equal size.

```sql
CREATE TABLE SYSTEM_LOGS
  (EVENT_NO NUMBER NOT NULL,
  EVENT_DATE DATE NOT NULL,
  EVENT_STR VARCHAR2(500),
  ERROR_CODE VARCHAR2(10))
  PARTITION BY HASH (ERROR_CODE)
  PARTITIONS 3
  STORE IN (TB1, TB2, TB3);
```

### List partitioning

Specify discrete values for the partition key per partition; gives explicit control over partition organization.

```sql
CREATE TABLE SYSTEM_LOGS
  (EVENT_NO NUMBER NOT NULL,
  EVENT_DATE DATE NOT NULL,
  EVENT_STR VARCHAR2(500),
  ERROR_CODE VARCHAR2(10))
  PARTITION BY LIST (ERROR_CODE)
  (PARTITION warning VALUES ('err1', 'err2', 'err3') TABLESPACE TB1,
  PARTITION critical VALUES ('err4', 'err5', 'err6') TABLESPACE TB2);
```

### Range partitioning

Rows are assigned by column values falling within a range. Most commonly used, often with date values (also works with numeric ranges).

```sql
CREATE TABLE SYSTEM_LOGS
  (EVENT_NO NUMBER NOT NULL,
  EVENT_DATE DATE NOT NULL,
  EVENT_STR VARCHAR2(500))
  PARTITION BY RANGE (EVENT_DATE)
  (PARTITION EVENT_DATE VALUES
    LESS THAN (TO_DATE('01/01/2015',
    'DD/MM/YYYY')) TABLESPACE TB1,
  PARTITION EVENT_DATE VALUES
    LESS THAN (TO_DATE('01/01/2016',
    'DD/MM/YYYY')) TABLESPACE TB2,
  PARTITION EVENT_DATE VALUES
    LESS THAN (TO_DATE('01/01/2017',
    'DD/MM/YYYY')) TABLESPACE TB3);
```

### Composite partitioning

A table is partitioned by one method and each partition subdivided into sub-partitions using the same or a different method, e.g. composite list-range, list-list, or range-hash.

### Partitioning extensions

- Manageability extensions: interval partitioning, partition advisor.
- Partitioning key extensions: reference partitioning, virtual column-based partitioning.

### Split partitions

Redistribute one partition/sub-partition into multiple.

```sql
ALTER TABLE SPLIT PARTITION p0 INTO
  (PARTITION P01 VALUES LESS THAN (100), PARTITION p02);
```

### Exchange partitions

Exchange table partitions in or out of a partitioned table.

```sql
ALTER TABLE orders EXCHANGE
  PARTITION p_ord3 WITH TABLE orders_year_2016;
```

### Subpartitioning

```sql
PARTITION BY RANGE(department_id)
  SUBPARTITION BY HASH(last_name)
  SUBPARTITION TEMPLATE
    (SUBPARTITION a TABLESPACE ts1,
    SUBPARTITION b TABLESPACE ts2,
    SUBPARTITION c TABLESPACE ts3,
    SUBPARTITION d TABLESPACE ts4)
  (PARTITION p1 VALUES LESS THAN (1000),
  PARTITION p2 VALUES LESS THAN (2000),
  PARTITION p3 VALUES LESS THAN (MAXVALUE)
```

### Automatic list partitioning (Oracle 12c)

Automatically creates a new partition for each new value inserted. The table starts with one partition; the database adds the rest.

```sql
CREATE TABLE SYSTEM_LOGS
  (EVENT_NO NUMBER NOT NULL,
  EVENT_DATE DATE NOT NULL,
  EVENT_STR VARCHAR2(500),
  ERROR_CODE VARCHAR2(10))
  PARTITION BY LIST (ERROR_CODE) AUTOMATIC
  (PARTITION warning VALUES ('err1', 'err2', 'err3'))
```

## MySQL

MySQL partitioning is similar to Oracle and supports most features. The unsupported items are the automatic features (interval partitioning, automatic list partitioning) — implement these with triggers or procedures.

> **Note:** Amazon RDS for MySQL 8 supports `ADD PARTITION`, `DROP PARTITION`, `COALESCE PARTITION`, `REORGANIZE PARTITION`, and `REBUILD PARTITION ALTER TABLE` with `ALGORITHM={COPY|INPLACE}` and `LOCK` clauses. `DROP PARTITION` with `ALGORITHM=INPLACE` deletes the partition's data and drops it; with `ALGORITHM=COPY` (or `old_alter_table=ON`) it rebuilds the table and moves data to a partition with a compatible `PARTITION … VALUES` definition, deleting data that cannot be moved.

### Hash partitioning

Use an SQL expression returning an integer for the hash. Allowed beyond integer are date types and these functions: `ABS, CEILING, DAY, DAYOFMONTH, DAYOFWEEK, DAYOFYEAR, DATEDIFF, EXTRACT, FLOOR, HOUR, MICROSECOND, MINUTE, MOD, MONTH, QUARTER, SECOND, TIME_TO_SEC, TO_DAYS, TO_SECONDS, UNIX_TIMESTAMP (with TIMESTAMP columns), WEEKDAY, YEAR, YEARWEEK`. For other column types use `KEY` partitioning (any column that is part or all of the primary key).

```sql
CREATE TABLE SYSTEM_LOGS
    (EVENT_NO INT NOT NULL,
    EVENT_DATE DATE NOT NULL,
    EVENT_STR VARCHAR(500),
    ERROR_CODE INT)
    PARTITION BY HASH (ERROR_CODE)
    PARTITIONS 3;
```

Key-partitioned table:

```sql
CREATE TABLE SYSTEM_LOGS
    (EVENT_NO INT NOT NULL,
    EVENT_DATE DATE NOT NULL,
    EVENT_STR VARCHAR(500),
    ERROR_CODE VARCHAR(10) PRIMARY KEY)
    PARTITION BY KEY()
    PARTITIONS 3;
```

### List partitioning

The partition column must be `INT`. To use `LIST` on `varchar`, use `LIST COLUMNS`.

```sql
CREATE TABLE SYSTEM_LOGS
    (EVENT_NO INT NOT NULL,
    EVENT_DATE DATE NOT NULL,
    EVENT_STR VARCHAR(500),
    ERROR_CODE INT)
    PARTITION BY LIST (ERROR_CODE)
    (PARTITION warning VALUES IN (3345, 5423,3332),
    PARTITION critical VALUES IN (9786, 9231, 6321));
```

List-columns partition:

```sql
CREATE TABLE SYSTEM_LOGS
    (EVENT_NO INT NOT NULL,
    EVENT_DATE DATE NOT NULL,
    EVENT_STR VARCHAR(500),
    ERROR_CODE VARCHAR(500))
    PARTITION BY LIST COLUMNS (ERROR_CODE)
    (PARTITION warning VALUES IN ('err1', 'err2', 'err3'),
    PARTITION critical VALUES IN ('err4', 'err5', 'err6'));
```

### Range partitioning

Use range on integer values, or `RANGE COLUMNS` for `DATE`/`DATETIME`.

```sql
CREATE TABLE SYSTEM_LOGS
    (EVENT_NO INT NOT NULL,
    EVENT_DATE DATE NOT NULL,
    EVENT_STR VARCHAR(500))
    PARTITION BY RANGE (YEAR(EVENT_DATE))
    (PARTITION p0 VALUES LESS THAN (2015),
    PARTITION p1 VALUES LESS THAN (2016),
    PARTITION p2 VALUES LESS THAN (2017));
```

Range-columns partition:

```sql
CREATE TABLE SYSTEM_LOGS
    (EVENT_NO INT NOT NULL,
    EVENT_DATE DATE NOT NULL,
    EVENT_STR VARCHAR(500))
    PARTITION BY RANGE COLUMNS (EVENT_DATE)
    (PARTITION p0 VALUES LESS THAN ('2015-01-01'),
    PARTITION p1 VALUES LESS THAN ('2016-01-01'),
    PARTITION p2 VALUES LESS THAN ('2017-01-01'));
```

### Composite partitioning

In MySQL 5.7 you can subpartition tables partitioned by range or list; subpartitions use hash or key partitioning. Either specify only the number of subpartitions per partition, or explicitly define them (to control names). All partitions must have the same number of subpartitions.

```sql
CREATE TABLE EMPLOYESS
    (DEPARTMENT_ID INT NOT NULL,
    LAST_NAME VARCHAR(50) NOT NULL,
    FIRST_NAME VARCHAR(50),
    PRIMARY KEY (DEPARTMENT_ID, LAST_NAME))
    PARTITION BY RANGE(DEPARTMENT_ID)
    SUBPARTITION BY KEY (last_name)
    SUBPARTITIONS 2
        (PARTITION p1 VALUES LESS THAN (10),
        PARTITION p2 VALUES LESS THAN (20),
        PARTITION p3 VALUES LESS THAN (MAXVALUE));
```

### Split partitions

Oracle's `SPLIT PARTITION` maps to MySQL `REORGANIZE PARTITION`. Range partitions can be split at the last partition only.

```sql
CREATE TABLE SYSTEM_LOGS
    (EVENT_NO INT NOT NULL,
    EVENT_DATE DATE NOT NULL,
    EVENT_STR VARCHAR(500),
    ERROR_CODE VARCHAR(500))
    PARTITION BY LIST COLUMNS (ERROR_CODE)
    (PARTITION warning VALUES IN ('err1', 'err2', 'err3'),
    PARTITION critical VALUES IN ('err4', 'err5', 'err6'));

ALTER TABLE SYSTEM_LOGS REORGANIZE PARTITION warning INTO
    (PARTITION warning0 VALUES IN ('err2.5', 'err3.5'),
    PARTITION warning1 VALUES IN ('err2.8', 'err3.8'));
```

### Exchange partitions

```sql
ALTER TABLE orders
    EXCHANGE PARTITION p_ord3 WITH TABLE orders_year_2016;
```

## Conversion notes

- Datatypes: change Oracle `NUMBER`/`VARCHAR2` to MySQL `INT`/`VARCHAR` in DDL.
- `STORE IN (tablespace...)` and `TABLESPACE` clauses are Oracle-specific and dropped in MySQL.
- MySQL hash/list partitioning requires an integer key/expression; use `KEY` partitioning, `LIST COLUMNS`, or `RANGE COLUMNS` for non-integer (e.g. varchar/date) columns.
- Oracle range-by-date `TO_DATE(...)` becomes MySQL `RANGE (YEAR(col))` or `RANGE COLUMNS (col)` with `'YYYY-MM-DD'` literals.
- `SPLIT PARTITION` → `REORGANIZE PARTITION` (range splits only at the last partition).
- `EXCHANGE PARTITION` is supported by both with nearly identical syntax.
- **Not supported in Aurora MySQL:** interval partitioning, partition advisor, preference partitioning, virtual column-based partitioning, automatic list partitioning. Emulate automatic features with triggers/procedures.

### Summary of Oracle partition types vs MySQL support

| Oracle table partition type | Built-in MySQL support |
|---|---|
| List | Yes |
| Range | Yes |
| Hash | Yes |
| Composite / subpartitioning | Yes |
| Interval | No |
| Partition advisor | No |
| Preference | No |
| Virtual column-based | No |
| Automatic list partitioning | No |
| Split and exchange | Yes |
