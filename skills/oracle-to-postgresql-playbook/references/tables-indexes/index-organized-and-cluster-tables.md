# Index-Organized and Cluster Tables

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.iot.html

**Conversion category:** Manual (two-star feature compatibility)
**SCT automation:** No automation. Indexes action code index. PostgreSQL doesn't support index-organized tables; a partial workaround exists.

## Oracle
An **index-organized table (IOT)** is an index/table hybrid. A normal (heap-organized) table stores rows unsorted; an IOT stores the actual table data inside a **B-tree index structure sorted by primary key**, with each leaf block holding both the PK and the non-key columns. This improves performance for primary-key access because rows are clustered/co-located by PK. Created with `ORGANIZATION INDEX`.

```sql
CREATE TABLE SYSTEM_EVENTS (
  EVENT_ID NUMBER,
  EVENT_CODE VARCHAR2(10) NOT NULL,
  EVENT_DESCIPTION VARCHAR2(200),
  EVENT_TIME DATE NOT NULL,
  CONSTRAINT PK_EVENT_ID PRIMARY KEY(EVENT_ID))
  ORGANIZATION INDEX;

INSERT INTO SYSTEM_EVENTS VALUES(9, 'EVNT-A1-10', 'Critical', '01-JAN-2017');
INSERT INTO SYSTEM_EVENTS VALUES(1, 'EVNT-C1-09', 'Warning', '01-JAN-2017');
INSERT INTO SYSTEM_EVENTS VALUES(7, 'EVNT-E1-14', 'Critical', '01-JAN-2017');

SELECT * FROM SYSTEM_EVENTS;   -- returned sorted by EVENT_ID: 1, 7, 9
```
Rows come back sorted in PK order (not insertion order) and **stay** sorted.

## PostgreSQL
No IOT support. The closest is the **`CLUSTER`** command, which physically sorts a table's data based on an existing index (e.g. the primary key).

**Key difference:** Oracle IOT sorting is defined at table creation and **persists** (always sorted). PostgreSQL `CLUSTER` is a **one-time** operation — subsequent inserts/updates are **not** clustered; you must re-run `CLUSTER` to re-sort.

```sql
CREATE TABLE SYSTEM_EVENTS (
  EVENT_ID NUMERIC,
  EVENT_CODE VARCHAR(10) NOT NULL,
  EVENT_DESCIPTION VARCHAR(200),
  EVENT_TIME DATE NOT NULL,
  CONSTRAINT PK_EVENT_ID PRIMARY KEY(EVENT_ID));

INSERT INTO SYSTEM_EVENTS VALUES(9, 'EV-A1-10', 'Critical', '01-JAN-2017');
INSERT INTO SYSTEM_EVENTS VALUES(1, 'EV-C1-09', 'Warning', '01-JAN-2017');
INSERT INTO SYSTEM_EVENTS VALUES(7, 'EV-E1-14', 'Critical', '01-JAN-2017');

CLUSTER SYSTEM_EVENTS USING PK_EVENT_ID;   -- now sorted 1,7,9

INSERT INTO SYSTEM_EVENTS VALUES(2, 'EV-E2-02', 'Warning', '01-JAN-2017');
-- new row (2) appended at end, NOT clustered

CLUSTER SYSTEM_EVENTS USING PK_EVENT_ID;   -- re-cluster -> 1,2,7,9
```

## Conversion notes
- No persistent IOT in PostgreSQL/Aurora — use `CLUSTER ... USING <index>` as a partial workaround.
- `CLUSTER` is one-time and not maintained on DML; schedule periodic re-clustering if PK-order locality matters.
- `CLUSTER` takes an exclusive lock and rewrites the table.
