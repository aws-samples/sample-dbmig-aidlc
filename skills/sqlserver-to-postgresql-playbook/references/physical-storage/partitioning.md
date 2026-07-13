# Partitioning Databases

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.storage.partitioning.html

**Conversion category:** Assisted (Two-star feature compatibility, three-star automation level)
**SCT automation:** Partitioning (AWS SCT action code: Partitioning). Key difference — PostgreSQL doesn't support `LEFT` partition or foreign keys referencing partitioned tables.

## SQL Server

SQL Server provides a logical and physical framework for partitioning table and index data. SQL Server 2017 supports up to 15,000 partitions. Partitioning is horizontal (sets of rows mapped to individual partitions). A partitioned table or index is a single object residing in a single schema within a single database.

All DQL and DML operations are partition agnostic except the special `$partition` predicate, which you can use for explicit partition elimination.

Partitioning uses three objects:

- **Partitioning column** — used by the partition function; its value determines the logical partition. Computed columns are allowed if explicitly `PERSISTED`. Must be a valid index column < 900 bytes, excluding timestamp and LOB types.
- **Partition function** — defines how partitioning-column values map to logical partitions and their boundaries.
- **Partition scheme** — maps logical partitions to file groups (physical OS files), enabling per-partition backup.

### Syntax

```sql
CREATE PARTITION FUNCTION <Partition Function>(<Data Type>)
AS RANGE [ LEFT | RIGHT ]
FOR VALUES (<Boundary Value 1>,...)[;]

CREATE PARTITION SCHEME <Partition Scheme>
AS PARTITION <Partition Function>
[ALL] TO (<File Group> | [ PRIMARY ] [,...])[;]

CREATE TABLE <Table Name> (<Table Definition>)
ON <Partition Schema> (<Partitioning Column>);
```

### Example

```sql
CREATE PARTITION FUNCTION PartitionFunction1 (INT)
AS RANGE LEFT FOR VALUES (1, 1000, 100000);

CREATE PARTITION SCHEME PartitionScheme1
AS PARTITION PartitionFunction1
ALL TO (PRIMARY);

CREATE TABLE PartitionTable (
  Col1 INT NOT NULL PRIMARY KEY,
  Col2 VARCHAR(20)
)
ON PartitionScheme1 (Col1);
```

## PostgreSQL

Starting with PostgreSQL 10, declarative partitioning provides an equivalent to SQL Server partitions using `RANGE` or `LIST` partitions (`HASH` added in PostgreSQL 11). You still create partition tables manually but no longer need triggers/functions to redirect data.

Prior to PostgreSQL 10, partitioning was implemented using table inheritance: each partition was a child table referencing an empty parent table.

PostgreSQL 11 added: default partitions, hash partitioning, partition-key `UPDATE` moving rows across partitions, index propagation to partitions, foreign-key propagation, and `FOR EACH ROW` trigger propagation.

### List partition

```sql
CREATE TABLE emps (
  emp_id SERIAL NOT NULL,
  emp_name VARCHAR(30) NOT NULL)
PARTITION BY LIST (left(lower(emp_name), 1));

CREATE TABLE emp_abc
  PARTITION OF emps (
  CONSTRAINT emp_id_nonzero CHECK (emp_id != 0)
) FOR VALUES IN ('a', 'b', 'c');

CREATE TABLE emp_def
  PARTITION OF emps (
  CONSTRAINT emp_id_nonzero CHECK (emp_id != 0)
) FOR VALUES IN ('d', 'e', 'f');

INSERT INTO emps VALUES (DEFAULT, 'Andrew');  -- row inserted
INSERT INTO emps VALUES (DEFAULT, 'Chris');   -- row inserted
INSERT INTO emps VALUES (DEFAULT, 'Frank');   -- row inserted
INSERT INTO emps VALUES (DEFAULT, 'Pablo');
-- SQL Error [23514]: ERROR: no partition of relation "emps" found for row
```

To prevent the error, ensure partitions exist for all possible values. The default partition feature (PostgreSQL 11) handles unmatched rows. For `RANGE` partitions, use `MAXVALUE`/`MINVALUE` in the `FROM/TO` clause to capture all values without risking missing partitions.

### Range partition

```sql
CREATE TABLE sales (
  saledate DATE NOT NULL,
  item_id INT,
  price FLOAT
) PARTITION BY RANGE (saledate);

CREATE TABLE sales_2018q1
  PARTITION OF sales (price DEFAULT 0)
  FOR VALUES FROM ('2018-01-01') TO ('2018-03-31');

CREATE TABLE sales_2018q2
  PARTITION OF sales (price DEFAULT 0)
  FOR VALUES FROM ('2018-04-01') TO ('2018-06-30');

CREATE TABLE sales_2018q3
  PARTITION OF sales (price DEFAULT 0)
  FOR VALUES FROM ('2018-07-01') TO ('2018-09-30');

INSERT INTO sales VALUES (('2018-01-08'),3121121, 100);
INSERT INTO sales VALUES (('2018-04-20'),4378623);
INSERT INTO sales VALUES (('2018-08-13'),3278621, 200);
```

When creating a table with `PARTITION OF`, you can also use `PARTITION BY` to create a sub-partition (same or different type as its parent).

### List combined with range sub-partition

```sql
CREATE TABLE salers (
  emp_id serial not null,
  emp_name varchar(30) not null,
  sales_in_usd int not null,
  sale_date date not null
) PARTITION BY LIST (left(lower(emp_name), 1));

CREATE TABLE emp_abc
  PARTITION OF salers (
  CONSTRAINT emp_id_nonzero CHECK (emp_id != 0)
) FOR VALUES IN ('a', 'b', 'c') PARTITION BY RANGE (sale_date);

CREATE TABLE emp_def
  PARTITION OF salers (
  CONSTRAINT emp_id_nonzero CHECK (emp_id != 0)
) FOR VALUES IN ('d', 'e', 'f') PARTITION BY RANGE (sale_date);

CREATE TABLE sales_abc_2018q1
  PARTITION OF emp_abc (sales_in_usd DEFAULT 0)
  FOR VALUES FROM ('2018-01-01') TO ('2018-03-31');
-- ... (additional quarterly sub-partitions for emp_abc / emp_def)
```

### Legacy: list partitioning with inheritance tables (pre-PostgreSQL 10)

1. Create a parent table from which all child tables inherit.
2. Create child tables inheriting from the parent with identical structure.
3. Create indexes on each child table; optionally add PK/check constraints.
4. Create a trigger to redirect data inserted into the parent to the right child.
5. Ensure `constraint_exclusion` is set to `partition`.

```sql
show constraint_exclusion;   -- constraint_exclusion = partition
```

Parent and child tables with check constraints:

```sql
CREATE TABLE SYSTEM_LOGS
  (EVENT_NO NUMERIC NOT NULL,
  EVENT_DATE DATE NOT NULL,
  EVENT_STR VARCHAR(500),
  ERROR_CODE VARCHAR(10));

CREATE TABLE SYSTEM_LOGS_WARNING (
  CHECK (ERROR_CODE IN('err1', 'err2', 'err3'))) INHERITS (SYSTEM_LOGS);

CREATE TABLE SYSTEM_LOGS_CRITICAL (
  CHECK (ERROR_CODE IN('err4', 'err5', 'err6'))) INHERITS (SYSTEM_LOGS);

CREATE INDEX IDX_SYSTEM_LOGS_WARNING ON SYSTEM_LOGS_WARNING(ERROR_CODE);
CREATE INDEX IDX_SYSTEM_LOGS_CRITICAL ON SYSTEM_LOGS_CRITICAL(ERROR_CODE);
```

Redirect trigger function and trigger:

```sql
CREATE OR REPLACE FUNCTION SYSTEM_LOGS_ERR_CODE_INS()
  RETURNS TRIGGER AS
  $$
  BEGIN
    IF (NEW.ERROR_CODE IN('err1', 'err2', 'err3')) THEN
      INSERT INTO SYSTEM_LOGS_WARNING VALUES (NEW.*);
    ELSIF (NEW.ERROR_CODE IN('err4', 'err5', 'err6')) THEN
      INSERT INTO SYSTEM_LOGS_CRITICAL VALUES (NEW.*);
    ELSE
      RAISE EXCEPTION 'Value out of range, check SYSTEM_LOGS_ERR_CODE_INS () Function!';
    END IF;
    RETURN NULL;
  END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER SYSTEM_LOGS_ERR_TRIG
  BEFORE INSERT ON SYSTEM_LOGS
  FOR EACH ROW EXECUTE PROCEDURE SYSTEM_LOGS_ERR_CODE_INS();
```

Notes for legacy inheritance partitioning:

- PostgreSQL 9.6 doesn't support declarative partitioning nor several SQL Server partitioning features.
- PostgreSQL 9.6 doesn't support foreign keys on the parent table — use triggers/functions or define them on individual tables.
- PostgreSQL doesn't support `SPLIT` and `EXCHANGE` of partitions — plan manual data migrations between tables instead.

### PostgreSQL 11 partitioning features

Default partition:

```sql
CREATE TABLE tst_part(i INT) PARTITION BY RANGE(i);
CREATE TABLE tst_part1 PARTITION OF tst_part FOR VALUES FROM (1) TO (5);
CREATE TABLE tst_part_dflt PARTITION OF tst_part DEFAULT;

INSERT INTO tst_part SELECT generate_series(1,10,1);
-- tst_part1 -> 1,2,3,4 ; tst_part_dflt -> 5..10
```

Hash partition:

```sql
CREATE TABLE tst_hash(i INT) PARTITION BY HASH(i);
CREATE TABLE tst_hash_1 PARTITION OF tst_hash FOR VALUES WITH (MODULUS 2, REMAINDER 0);
CREATE TABLE tst_hash_2 PARTITION OF tst_hash FOR VALUES WITH (MODULUS 2, REMAINDER 1);
```

`UPDATE` on partition key moves rows across partitions:

```sql
UPDATE tst_part SET i=1 WHERE i IN (5,6);
-- rows move from default partition into tst_part1
```

Index, foreign-key, and trigger propagation:

```sql
CREATE INDEX tst_part_ind ON tst_part(i);
-- corresponding indexes created on each partition automatically

CREATE TABLE tst_ref(i INT PRIMARY KEY);
ALTER TABLE tst_part ADD CONSTRAINT tst_part_fk FOREIGN KEY (i) REFERENCES tst_ref(i);
-- FK propagated to each partition

CREATE TRIGGER some_trigger AFTER UPDATE ON tst_part
  FOR EACH ROW EXECUTE FUNCTION some_func();
-- trigger propagated to each partition
```

For more information, see [Table Partitioning](https://www.postgresql.org/docs/13/ddl-partitioning.html) in the PostgreSQL documentation.

## Conversion notes

- SQL Server supports `RANGE` partitioning only; PostgreSQL supports `RANGE` and `LIST` (plus `HASH` from v11).
- Partition boundary direction: SQL Server allows `LEFT` or `RIGHT`; PostgreSQL is `RIGHT` only — `LEFT` partition definitions must be rewritten.
- `EXCHANGE`/`SPLIT` partition: available in SQL Server; not available in PostgreSQL (N/A) — plan manual data movement.
- Foreign keys referencing a partitioned table are not supported in PostgreSQL (FKs *from* a partitioned table propagate to partitions in v11+).
- SQL Server uses partition functions + partition schemes mapped to file groups; PostgreSQL uses declarative `PARTITION BY`/`PARTITION OF` (or legacy inheritance + redirect triggers pre-v10).
- SCT provides three-star automation for partitioning, but two-star feature compatibility means manual review/rewrite is still expected, especially for `LEFT` boundaries, `EXCHANGE`/`SPLIT`, and FK references.

### Summary comparison

| Feature | SQL Server | Aurora PostgreSQL |
|---|---|---|
| Partition types | `RANGE` only | `RANGE`, `LIST` (`HASH` v11+) |
| Partition boundary direction | `LEFT` or `RIGHT` | `RIGHT` |
| Exchange partition | Any partition to any partition | N/A |
| Partition function | Abstract function object | Abstract function object |
| Partition scheme | Abstract storage mapping object | Abstract storage mapping object |
| Limitations | None — all tables partitioned | Not all commands compatible with table inheritance |
