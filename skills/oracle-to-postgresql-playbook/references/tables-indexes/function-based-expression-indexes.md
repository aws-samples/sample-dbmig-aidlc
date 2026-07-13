# Function-Based / Expression Indexes

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.expression.html

**Conversion category:** Automatic (four-star feature compatibility, four-star automation)
**SCT automation:** Indexes action code index. PostgreSQL doesn't support functional indexes that aren't single-column.

## Oracle
Function-based indexes store the output of a function applied to column values, allowing functions in the `WHERE` clause to use the index. The optimizer uses it only when the function appears in the query. Oracle updates the index on each DML so the function result stays correct.

```sql
CREATE TABLE SYSTEM_EVENTS(
  EVENT_ID NUMERIC PRIMARY KEY,
  EVENT_CODE VARCHAR2(10) NOT NULL,
  EVENT_DESCIPTION VARCHAR2(200),
  EVENT_TIME TIMESTAMP NOT NULL);

CREATE INDEX EVNT_BY_DAY ON SYSTEM_EVENTS(
  EXTRACT(DAY FROM EVENT_TIME));
```

## PostgreSQL
PostgreSQL **expression indexes** are equivalent to Oracle function-based indexes.

```sql
CREATE TABLE system_events(
  event_id NUMERIC PRIMARY KEY,
  event_code VARCHAR(21) NOT NULL,
  event_description VARCHAR(200),
  event_time TIMESTAMP NOT NULL);

CREATE INDEX event_by_day ON system_events(EXTRACT(DAY FROM event_time));
```

Verify usage after loading data and running `ANALYZE`:
```sql
INSERT INTO system_events
  SELECT ID AS event_id,
    'EVNT-A'||ID+9||'-'||ID AS event_code,
    CASE WHEN mod(ID,2) = 0 THEN 'Warning' ELSE 'Critical' END AS event_desc,
    now() + INTERVAL '1 minute' * ID AS event_time
  FROM (SELECT generate_series(1,1000000) AS ID) A;

ANALYZE SYSTEM_EVENTS;

EXPLAIN SELECT * FROM SYSTEM_EVENTS
  WHERE EXTRACT(DAY FROM EVENT_TIME) = '22';
-- Bitmap Heap Scan on system_events
--   Recheck Cond: (date_part('day', event_time) = '22'::double precision)
--   -> Bitmap Index Scan on evnt_by_day
--        Index Cond: (date_part('day', event_time) = '22'::double precision)
```

### Partial indexes (PostgreSQL-specific)
PostgreSQL also supports **partial indexes** — an index with a `WHERE` clause, indexing only a relevant subset of rows to increase efficiency and reduce index size.

```sql
CREATE TABLE SYSTEM_EVENTS(
  EVENT_ID NUMERIC PRIMARY KEY,
  EVENT_CODE VARCHAR(10) NOT NULL,
  EVENT_DESCIPTION VARCHAR(200),
  EVENT_TIME DATE NOT NULL);

CREATE INDEX IDX_TIME_CODE ON SYSTEM_EVENTS(EVENT_TIME)
  WHERE EVENT_CODE like '01-A%';
```

## Conversion notes
- Oracle function-based index → PostgreSQL expression index, near-identical syntax.
- PostgreSQL supports only **single-column** functional/expression indexes (the key difference flagged by SCT).
- Consider PostgreSQL **partial indexes** (`WHERE` predicate) as an additional optimization not available in Oracle.
- Run `ANALYZE` after data load so the planner has statistics to choose the expression index.
