# Oracle Table Partitioning and PostgreSQL Partitions and Table Inheritance

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.storage.partition.html

**Conversion category:** Assisted (Three-star feature compatibility, three-star AWS SCT/DMS automation level). List, Range, and Hash partitioning map directly via declarative partitioning (PostgreSQL 10+); composite/interval/reference/virtual-column/automatic-list/split/exchange require manual workarounds.
**SCT automation:** Three-star automation level. AWS SCT action code index: N/A. Key difference: foreign keys referencing to/from partitioned tables are supported on individual tables in PostgreSQL; some Oracle partition types are unsupported.

## Oracle

Partitioning divides large tables and indexes into smaller pieces (partitions), each with its own name and definition, managed separately or collectively. Partitions are transparent to applications (unmodified SQL works). Benefits: query performance (scan a subset; parallel DML/DDL), data management/ILM (migration, index maintenance, backup/recovery), and reduced maintenance downtime.

Oracle 18c adds online merging of partitions/subpartitions (concurrent with DML) and online/offline modification of partitioning strategy (e.g., hash → range). Oracle 19c adds hybrid partitioned tables (mixing internal Oracle tables and external tables/sources in one partitioned table).

### Hash table partitioning

A hashing algorithm evenly distributes records across all partitions (approximately equal size).

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

### List table partitioning

Specify discrete values for the partition key per partition, giving explicit control over partition organization.

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

### Range table partitioning

Rows are assigned to partitions based on column values falling within a range. Most frequently used type, primarily with date values (also numeric ranges).

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

### Composite table partitioning

A table is partitioned by one method, and each partition further subdivided into subpartitions using the same or a different method. Examples: composite list-range, list-list, range-hash.

### Partitioning extensions

- Manageability extensions: interval partitioning, partition advisor.
- Partitioning key extensions: reference partitioning, virtual column-based partitioning.

### Split partitions

`SPLIT PARTITION` redistributes one partition/subpartition into multiple.

```sql
ALTER TABLE SPLIT PARTITION p0 INTO
  (PARTITION P01 VALUES LESS THAN (100), PARTITION p02);
```

### Exchange partitions

`EXCHANGE PARTITION` swaps table partitions in or out of a partitioned table.

```sql
ALTER TABLE orders EXCHANGE
  PARTITION p_ord3 WITH TABLE orders_year_2016;
```

### Subpartitioning tables

Subpartitions further split a parent partition.

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

Automatically creates new partitions for new values inserted into a list-partitioned table. The table starts with one partition; the database adds more automatically.

```sql
CREATE TABLE SYSTEM_LOGS
  (EVENT_NO NUMBER NOT NULL,
  EVENT_DATE DATE NOT NULL,
  EVENT_STR VARCHAR2(500),
  ERROR_CODE VARCHAR2(10))
  PARTITION BY LIST (ERROR_CODE) AUTOMATIC
  (PARTITION warning VALUES ('err1', 'err2', 'err3'))
```

## PostgreSQL

Starting with PostgreSQL 10, declarative partitioning provides an equivalent to Oracle partitions for `RANGE` and `LIST`. Before PG 10, partitioning used table inheritance: each partition was a child table referencing a single, empty parent table (used as metadata dictionary and query source), requiring triggers/functions to route data. In PG 10 you still create partition tables manually but no longer need triggers/functions for routing. Some management operations run directly on subpartitions (sub-tables); querying runs on the partitioned table itself.

PostgreSQL 11 and 12 added:
- Default partition to store data that can't be routed to any explicit partition.
- Hash key partitioning (in addition to range and list).
- `UPDATE` on a partition-key column moves data to the proper partition.
- Indexes on a partitioned table propagate to individual partitions automatically.
- Foreign keys on a partitioned table propagate to individual partitions.
- `FOR EACH ROW` triggers on a partitioned table propagate to individual partitions.
- Attaching/detaching a partition correctly propagates foreign-key enforcement triggers.

### Using the partition mechanism

#### List partition

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

INSERT INTO emps VALUES (DEFAULT, 'Andrew');   -- row inserted
INSERT INTO emps VALUES (DEFAULT, 'Chris');    -- row inserted
INSERT INTO emps VALUES (DEFAULT, 'Frank');    -- row inserted

INSERT INTO emps VALUES (DEFAULT, 'Pablo');
-- SQL Error [23514]: ERROR: no partition of relation "emps" found for row
-- Detail: Partition key of the failing row contains
--   ("left"(lower(emp_name::text), 1)) = (p).
```

To prevent the error, ensure partitions exist for all possible key values. The default partition (PG 11+) handles this. For `RANGE` partitions, use `MAXVALUE`/`MINVALUE` in the `FROM/TO` clause to capture all values without risking new partitions.

#### Range partition

```sql
CREATE TABLE sales (
  saledate DATE NOT NULL,
  item_id INT,
  price FLOAT
) PARTITION BY RANGE (saledate);

CREATE TABLE sales_2018q1
  PARTITION OF sales (
    price DEFAULT 0
  ) FOR VALUES FROM ('2018-01-01') TO ('2018-03-31');

CREATE TABLE sales_2018q2
  PARTITION OF sales (
    price DEFAULT 0
  ) FOR VALUES FROM ('2018-04-01') TO ('2018-06-30');

CREATE TABLE sales_2018q3
  PARTITION OF sales (
    price DEFAULT 0
  ) FOR VALUES FROM ('2018-07-01') TO ('2018-09-30');

INSERT INTO sales VALUES (('2018-01-08'),3121121, 100);  -- row inserted
INSERT INTO sales VALUES (('2018-04-20'),4378623);       -- row inserted
INSERT INTO sales VALUES (('2018-08-13'),3278621, 200);  -- row inserted
```

Using `PARTITION BY` together with `PARTITION OF` creates a sub-partition. A sub-partition can be the same type as the parent or a different partition type.

#### List combined with range (sub-partitioning)

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
CREATE TABLE sales_abc_2018q2
  PARTITION OF emp_abc (sales_in_usd DEFAULT 0)
  FOR VALUES FROM ('2018-04-01') TO ('2018-06-30');
CREATE TABLE sales_abc_2018q3
  PARTITION OF emp_abc (sales_in_usd DEFAULT 0)
  FOR VALUES FROM ('2018-07-01') TO ('2018-09-30');

CREATE TABLE sales_def_2018q1
  PARTITION OF emp_def (sales_in_usd DEFAULT 0)
  FOR VALUES FROM ('2018-01-01') TO ('2018-03-31');
CREATE TABLE sales_def_2018q2
  PARTITION OF emp_def (sales_in_usd DEFAULT 0)
  FOR VALUES FROM ('2018-04-01') TO ('2018-06-30');
CREATE TABLE sales_def_2018q3
  PARTITION OF emp_def (sales_in_usd DEFAULT 0)
  FOR VALUES FROM ('2018-07-01') TO ('2018-09-30');
```

### Implementing list partitioning with inheritance tables (pre-PG 10 approach)

1. Create a parent table from which all child tables (partitions) inherit.
2. Create child tables with identical structure to the parent (acting like partitions).
3. Create indexes on each child table; optionally add constraints (primary keys or check constraints) to define allowed values.
4. Create a trigger to redirect inserts from the parent to the appropriate child.
5. Ensure `constraint_exclusion` is set to `partition` so queries are optimized.

```sql
show constraint_exclusion;
-- constraint_exclusion
-- ----------------------
-- partition
```

Notes on PostgreSQL 9.6: it does not support declarative partitioning or several Oracle features. Replace Oracle interval partitioning with application-centric methods (PL/pgSQL or other languages). PG 9.6 does not support foreign keys on the parent table (use triggers/functions or create FKs on individual tables). PostgreSQL does not support `SPLIT`/`EXCHANGE` of partitions — plan data migrations manually between tables.

#### Inheritance example — list partitioning

```sql
-- Parent table
CREATE TABLE SYSTEM_LOGS
  (EVENT_NO NUMERIC NOT NULL,
  EVENT_DATE DATE NOT NULL,
  EVENT_STR VARCHAR(500),
  ERROR_CODE VARCHAR(10));

-- Child tables (partitions) with check constraints
CREATE TABLE SYSTEM_LOGS_WARNING (
  CHECK (ERROR_CODE IN('err1', 'err2', 'err3'))) INHERITS (SYSTEM_LOGS);
CREATE TABLE SYSTEM_LOGS_CRITICAL (
  CHECK (ERROR_CODE IN('err4', 'err5', 'err6'))) INHERITS (SYSTEM_LOGS);

-- Indexes on each child
CREATE INDEX IDX_SYSTEM_LOGS_WARNING ON SYSTEM_LOGS_WARNING(ERROR_CODE);
CREATE INDEX IDX_SYSTEM_LOGS_CRITICAL ON SYSTEM_LOGS_CRITICAL(ERROR_CODE);

-- Redirect function
CREATE OR REPLACE FUNCTION SYSTEM_LOGS_ERR_CODE_INS()
  RETURNS TRIGGER AS
  $$
  BEGIN
    IF (NEW.ERROR_CODE IN('err1', 'err2', 'err3')) THEN
      INSERT INTO SYSTEM_LOGS_WARNING VALUES (NEW.*);
    ELSIF (NEW.ERROR_CODE IN('err4', 'err5', 'err6')) THEN
      INSERT INTO SYSTEM_LOGS_CRITICAL VALUES (NEW.*);
    ELSE
      RAISE EXCEPTION 'Value out of range,
        check SYSTEM_LOGS_ERR_CODE_INS () Function!';
    END IF;
  RETURN NULL;
  END;
$$
LANGUAGE plpgsql;

-- Attach trigger
CREATE TRIGGER SYSTEM_LOGS_ERR_TRIG
  BEFORE INSERT ON SYSTEM_LOGS
  FOR EACH ROW EXECUTE PROCEDURE SYSTEM_LOGS_ERR_CODE_INS();

-- Insert into parent
INSERT INTO SYSTEM_LOGS VALUES(1, '2015-05-15', 'a...', 'err1');
INSERT INTO SYSTEM_LOGS VALUES(2, '2016-06-16', 'b...', 'err3');
INSERT INTO SYSTEM_LOGS VALUES(3, '2017-07-17', 'c...', 'err6');

-- Results visible across child tables
SELECT * FROM SYSTEM_LOGS;          -- all 3 rows
SELECT * FROM SYSTEM_LOGS_WARNING;  -- err1, err3 rows
SELECT * FROM SYSTEM_LOGS_CRITICAL; -- err6 row
```

#### Inheritance example — range partitioning

```sql
-- Parent table
CREATE TABLE SYSTEM_LOGS
  (EVENT_NO NUMERIC NOT NULL,
  EVENT_DATE DATE NOT NULL,
  EVENT_STR VARCHAR(500));

-- Child tables with check constraints
CREATE TABLE SYSTEM_LOGS_2015
  (CHECK (EVENT_DATE >= DATE '2015-01-01'
    AND EVENT_DATE < DATE '2016-01-01'))
  INHERITS (SYSTEM_LOGS);
CREATE TABLE SYSTEM_LOGS_2016
  (CHECK (EVENT_DATE >= DATE '2016-01-01'
    AND EVENT_DATE < DATE '2017-01-01'))
  INHERITS (SYSTEM_LOGS);
CREATE TABLE SYSTEM_LOGS_2017
  (CHECK (EVENT_DATE >= DATE '2017-01-01'
    AND EVENT_DATE <= DATE '2017-12-31'))
  INHERITS (SYSTEM_LOGS);

-- Indexes
CREATE INDEX IDX_SYSTEM_LOGS_2015 ON SYSTEM_LOGS_2015(EVENT_DATE);
CREATE INDEX IDX_SYSTEM_LOGS_2016 ON SYSTEM_LOGS_2016(EVENT_DATE);
CREATE INDEX IDX_SYSTEM_LOGS_2017 ON SYSTEM_LOGS_2017(EVENT_DATE);

-- Redirect function
CREATE OR REPLACE FUNCTION SYSTEM_LOGS_INS ()
  RETURNS TRIGGER AS
  $$
  BEGIN
    IF (NEW.EVENT_DATE >= DATE '2015-01-01'
      AND NEW.EVENT_DATE < DATE '2016-01-01') THEN
        INSERT INTO SYSTEM_LOGS_2015 VALUES (NEW.*);
    ELSIF (NEW.EVENT_DATE >= DATE '2016-01-01'
      AND NEW.EVENT_DATE < DATE '2017-01-01') THEN
        INSERT INTO SYSTEM_LOGS_2016 VALUES (NEW.*);
    ELSIF (NEW.EVENT_DATE >= DATE '2017-01-01'
      AND NEW.EVENT_DATE <= DATE '2017-12-31') THEN
        INSERT INTO SYSTEM_LOGS_2017 VALUES (NEW.*);
    ELSE
      RAISE EXCEPTION 'Date out of range.
        check SYSTEM_LOGS_INS () function!';
    END IF;
  RETURN NULL;
  END;
$$
LANGUAGE plpgsql;

-- Attach trigger
CREATE TRIGGER SYSTEM_LOGS_TRIG BEFORE INSERT ON SYSTEM_LOGS
  FOR EACH ROW EXECUTE PROCEDURE SYSTEM_LOGS_INS ();

-- Insert into parent
INSERT INTO SYSTEM_LOGS VALUES (1, '2015-05-15', 'a...');
INSERT INTO SYSTEM_LOGS VALUES (2, '2016-06-16', 'b...');
INSERT INTO SYSTEM_LOGS VALUES (3, '2017-07-17', 'c...');

SELECT * FROM SYSTEM_LOGS;       -- all 3 rows
SELECT * FROM SYSTEM_LOGS_2015;  -- 2015 row only
```

### New partitioning features (PostgreSQL 11)

Default partitions:

```sql
CREATE TABLE tst_part(i INT) PARTITION BY RANGE(i);
CREATE TABLE tst_part1 PARTITION OF tst_part FOR VALUES FROM (1) TO (5);
CREATE TABLE tst_part_dflt PARTITION OF tst_part DEFAULT;
INSERT INTO tst_part SELECT generate_series(1,10,1);
-- tst_part1: 1,2,3,4   tst_part_dflt: 5,6,7,8,9,10
```

Hash partitioning:

```sql
CREATE TABLE tst_hash(i INT) PARTITION BY HASH(i);
CREATE TABLE tst_hash_1 PARTITION OF tst_hash FOR VALUES WITH (MODULUS 2, REMAINDER 0);
CREATE TABLE tst_hash_2 PARTITION OF tst_hash FOR VALUES WITH (MODULUS 2, REMAINDER 1);
INSERT INTO tst_hash SELECT generate_series(1,10,1);
-- tst_hash_1: 1,2   tst_hash_2: 3,4,5,6,7,8,9,10
```

`UPDATE` on partition key moves rows:

```sql
UPDATE tst_part SET i=1 WHERE i IN (5,6);
-- rows 5,6 move from tst_part_dflt into tst_part1
```

Index propagation, foreign-key propagation, and trigger propagation all flow automatically from the partitioned parent to individual partitions:

```sql
CREATE INDEX tst_part_ind ON tst_part(i);
-- Each partition gets its own index (e.g., tst_part1_i_idx, tst_part2_i_idx)

CREATE TABLE tst_ref(i INT PRIMARY KEY);
ALTER TABLE tst_part ADD CONSTRAINT tst_part_fk FOREIGN KEY (i) REFERENCES tst_ref(i);
-- FK constraint propagates to each partition

CREATE TRIGGER some_trigger AFTER UPDATE ON tst_part
  FOR EACH ROW EXECUTE FUNCTION some_func();
-- Trigger propagates to each partition
```

## Conversion notes

### Mechanical rule: `VALUES LESS THAN` → two-sided bounds

Oracle range partitions declare only an **upper** bound; PostgreSQL requires **both**. Carry the
previous partition's bound forward as the next partition's lower bound, starting at `MINVALUE`:

```sql
-- Oracle (upper bound only, implicitly starting where the previous one ended)
PARTITION BY RANGE ("C_TRIP_DATE")
 (PARTITION "P18" VALUES LESS THAN (TO_DATE(' 2019-01-01 00:00:00', ...)),
  PARTITION "P19" VALUES LESS THAN (TO_DATE(' 2020-01-01 00:00:00', ...)))

-- PostgreSQL (explicit FROM ... TO ...; note FROM is inclusive, TO is exclusive)
CREATE TABLE t (...) PARTITION BY RANGE (c_trip_date);
CREATE TABLE p18 PARTITION OF t FOR VALUES FROM (MINVALUE)              TO ('2019-01-01 00:00:00');
CREATE TABLE p19 PARTITION OF t FOR VALUES FROM ('2019-01-01 00:00:00') TO ('2020-01-01 00:00:00');
CREATE TABLE t_default PARTITION OF t DEFAULT;   -- always; see below
```

The first partition must start at `MINVALUE`, not at the first data value — otherwise rows older
than the earliest bound have nowhere to go. Oracle's `MAXVALUE` upper partition becomes
`TO (MAXVALUE)`.

### Always add a `DEFAULT` partition — this is a *runtime* failure

Oracle range partitioning routes NULL and out-of-range keys to a catch-all; PostgreSQL
**rejects the insert** with `SQLSTATE 23514 — no partition of relation "t" found for row`.
Without a `DEFAULT` partition the application starts failing *after* go-live, on data the
migration never saw — the worst failure class, because nothing in the conversion or a schema
diff reveals it.

```sql
CREATE TABLE t_default PARTITION OF t DEFAULT;
```

Add one to **every** partitioned table, including list-partitioned ones (Oracle's automatic list
partitioning has no equivalent, so new values would otherwise be rejected).

### PK / UNIQUE on a partitioned table must include the partition key

PostgreSQL cannot create a unique index spanning partitions unless it contains every
partitioning column:

```
ERROR:  unique constraint on partitioned table must include all partitioning columns
```

Oracle supports a **global** unique index that excludes the partition key; PostgreSQL does not.
Options, in order of preference:

1. **Add the partition key to the constraint** — mechanical and keeps a usable key, but it
   **weakens uniqueness** from global to per-partition-key-value. This is a *semantic change*:
   two rows that Oracle would have rejected can now both exist in different partitions.
2. Enforce global uniqueness in the application, or via a separate mechanism.
3. Drop the constraint if it existed only to create an index.

**Never apply option 1 silently.** Annotate every occurrence inline (`-- NOTE:`) and have a
reviewer sign it off.

Related: `DEFERRABLE` unique constraints are **not supported on partitioned tables**, so
Oracle's deferred-to-`COMMIT` uniqueness checking becomes per-statement checking — another
behaviour change to flag.

### Partition names are schema-global in PostgreSQL

Oracle scopes partition names **per table**, so two tables may each have a partition named
`P3M239_19`. PostgreSQL partitions are ordinary relations in the schema, so identical names
collide:

```
ERROR:  relation "p3m239_19" already exists
```

Track emitted partition names **globally** across the schema and disambiguate on collision by
prefixing the parent table name, then truncating to PostgreSQL's **63-byte** identifier limit
(watch for truncation itself creating a new collision).

### Row triggers clone to every partition — expect inflated catalog counts

A `FOR EACH ROW` trigger declared on a partitioned parent is **cloned onto every partition**.
In one migration 175 declared triggers produced **668** rows in `pg_trigger`. This is correct
behaviour, but it means:

- trigger counts will **not** match the Oracle source, so a naive count-based reconciliation
  reports a false mismatch;
- compare **parent declarations**, not raw catalog rows (`pg_dump` re-emits only the parent
  declarations, which is the right granularity);
- the same cloning applies to indexes and foreign keys declared on the parent.

### Built-in support by Oracle partition type

- Built-in PostgreSQL support by Oracle partition type:

  | Oracle table partition type | Built-in PostgreSQL support |
  |---|---|
  | List | Yes |
  | Range | Yes |
  | Hash | Yes |
  | Composite partitioning (sub-partitioning) | No |
  | Interval partitioning | No |
  | Partition advisor | No |
  | Reference partitioning | No |
  | Virtual column-based partitioning | No |
  | Automatic list partitioning | No |
  | Split / exchange partitions | No |

- List, Range, and Hash convert cleanly to declarative partitioning on PostgreSQL 10/11+. Hash partitioning needs PG 11+.
- Composite/sub-partitioning is not "built-in" as a single declarative construct, but can be emulated by nesting `PARTITION BY` inside `PARTITION OF` (a sub-partition may differ in type from the parent).
- Interval partitioning has no equivalent — implement application-centric partition creation (PL/pgSQL or app code). The default partition (PG 11+) helps capture out-of-range rows that interval partitioning would otherwise auto-create.
- Automatic list partitioning is unsupported — pre-create all partitions or use a default partition to avoid the `23514` "no partition found for row" error.
- `SPLIT` and `EXCHANGE` partition operations are not supported in PostgreSQL — plan manual data movement between tables.
- Foreign keys referencing to/from partitioned tables are supported on the individual tables; PG 11+ propagates FKs, indexes, and row-level triggers from the parent to partitions automatically.
- Pre-PG 10 (e.g., PG 9.6) requires the inheritance + trigger/function routing pattern and `constraint_exclusion = partition`; FKs on the parent are not supported there.
- Aurora PostgreSQL follows the same partitioning capabilities as the corresponding community PostgreSQL major version; choose a version (11+) that includes hash partitioning, default partitions, and propagation features to minimize manual work. AWS DMS can migrate the underlying data into the target partitioned structure.
