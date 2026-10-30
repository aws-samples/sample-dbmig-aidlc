# Service Broker

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.servicebroker.html

**Conversion category:** Manual (no feature compatibility, no automation)
**SCT automation:** No automation — SCT action code index: Service Broker

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): Added verified in-database queue pattern (FOR UPDATE SKIP LOCKED, pg_notify), aws_lambda 2.1 / dblink / pg_cron options, pgmq not available, SQS FIFO for ordered delivery.

## SQL Server

SQL Server Service Broker provides native messaging and queuing inside the database engine, used to build distributed, reliable, decoupled applications. Benefits: decouple application dependencies via messages, scale out by moving queues/processors to separate servers, maintain parts with minimal user impact, control when messages process (off-peak), and process on multiple servers/threads.

Core commands:

**CREATE MESSAGE TYPE** — defines a message name and structure (validation NONE/EMPTY/WELL_FORMED_XML/VALID_XML).

```sql
CREATE MESSAGE TYPE message_type_name
  [ AUTHORIZATION owner_name ]
  [ VALIDATION = { NONE
    | EMPTY
    | WELL_FORMED_XML
    | VALID_XML WITH SCHEMA COLLECTION schema_collection_name
  } ]
[ ; ]
```

**CREATE QUEUE** — creates a queue to store messages.

```sql
CREATE QUEUE <object>
  [ WITH
    [ STATUS = { ON | OFF } [ , ] ]
    [ RETENTION = { ON | OFF } [ , ] ]
    [ ACTIVATION (
      [ STATUS = { ON | OFF } , ]
        PROCEDURE_NAME = <procedure> ,
        MAX_QUEUE_READERS = max_readers ,
        EXECUTE AS { SELF | 'user_name' | OWNER }
        ) [ , ] ]
    [ POISON_MESSAGE_HANDLING (
      [ STATUS = { ON | OFF } ] ) ]
    ]
      [ ON { filegroup | [ DEFAULT ] } ]
[ ; ]
```

**CREATE CONTRACT** — specifies the role and what message types a service handles.

```sql
CREATE CONTRACT contract_name
  [ AUTHORIZATION owner_name ]
    ( { { message_type_name | [ DEFAULT ] }
      SENT BY { INITIATOR | TARGET | ANY }
    } [ ,...n] )
[ ; ]
```

**CREATE SERVICE** — creates a named Service Broker for a task set.

```sql
CREATE SERVICE service_name
  [ AUTHORIZATION owner_name ]
  ON QUEUE [ schema_name. ]queue_name
  [ ( contract_name | [DEFAULT][ ,...n ] ) ]
[ ; ]
```

**BEGIN DIALOG CONVERSATION** — starts interaction between Service Brokers.

```sql
BEGIN DIALOG [ CONVERSATION ] @dialog_handle
  FROM SERVICE initiator_service_name
  TO SERVICE 'target_service_name'
    [ , { 'service_broker_guid' | 'CURRENT DATABASE' }]
  [ ON CONTRACT contract_name ]
  [ WITH
  [ { RELATED_CONVERSATION = related_conversation_handle
    | RELATED_CONVERSATION_GROUP = related_conversation_group_id } ]
  [ [ , ] LIFETIME = dialog_lifetime ]
  [ [ , ] ENCRYPTION = { ON | OFF } ] ]
[ ; ]
```

**WAITFOR(RECEIVE TOP(1))** — block until a message is received.

```sql
[ WAITFOR ( ]
  RECEIVE [ TOP ( n ) ]
  <column_specifier> [ ,...n ]
  FROM <queue>
  [ INTO table_variable ]
  [ WHERE { conversation_handle = conversation_handle
    | conversation_group_id = conversation_group_id } ]
  [ ) ] [ , TIMEOUT timeout ]
[ ; ]
```

## PostgreSQL

Aurora PostgreSQL has **no compatible equivalent** to SQL Server Service Broker. Achieve similar functionality with a combination of AWS services:

- **DB Links + tables**: create a table in each database, connect them with a DB link, and read/process the data across databases.
- **AWS Lambda**: query a table, process the data, and insert it into another database (even a different engine). Best option for moving workloads off the database to a cheaper instance type.
- **Amazon SQS + AWS Lambda**: for maximum decoupling and to remove load from the database — more efficient and cost-effective. See "Using Lambda with Amazon SQS".

### In-database options on Aurora PostgreSQL 18 (verified on 18.6)

When the queue must stay transactional with the data (the main reason Service Broker was used), a queue table with `FOR UPDATE SKIP LOCKED` gives competing consumers without blocking:

```sql
CREATE TABLE app.msg_queue (
  id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  msg_type text NOT NULL,
  body    jsonb NOT NULL,
  enqueued_at timestamptz NOT NULL DEFAULT now());

-- SEND ON CONVERSATION  →
INSERT INTO app.msg_queue (msg_type, body) VALUES ('OrderCreated', '{"id": 42}');

-- RECEIVE TOP(1) … FROM queue  →  (each consumer gets a different row; locked rows are skipped)
WITH next AS (SELECT id FROM app.msg_queue ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1)
DELETE FROM app.msg_queue q USING next WHERE q.id = next.id
RETURNING q.id, q.msg_type, q.body;
```

- `WAITFOR (RECEIVE …), TIMEOUT` → the consumer polls, or waits on `LISTEN app_queue` and the producer runs `pg_notify('app_queue', id::text)` in the same transaction (the notification is delivered at commit). `LISTEN` needs a persistent client connection; it does not work through RDS Proxy pinning-free mode or the Data API.
- Activation procedures (`ACTIVATION (PROCEDURE_NAME = …)`) → a `pg_cron` job that drains the queue, or an external worker (Lambda on a schedule, ECS task).
- Calling out from the database: the `aws_lambda` extension (2.1 on 18.6) invokes a Lambda function from SQL (`aws_lambda.invoke`), for example from an `AFTER INSERT` trigger. Keep such calls asynchronous (`'Event'` invocation type) so a slow function does not hold row locks.
- Cross-database dialogs → `dblink` 1.2 / `postgres_fdw` 1.2, or (better) put both sides on SQS.
- The `pgmq` extension is **not** available on Aurora PostgreSQL 18.6.
- Message types with `VALIDATION = WELL_FORMED_XML` → a `CHECK` constraint on an `xml`/`jsonb` body; conversation groups and ordering guarantees must be designed in the queue table (for example a `conversation_id` column plus `ORDER BY id`).
- Queue tables churn heavily: give them aggressive per-table autovacuum settings (`autovacuum_vacuum_scale_factor = 0`, `autovacuum_vacuum_threshold = 1000`) or partition by time with `pg_partman` and drop old partitions.

## Conversion notes
- No native equivalent — migration requires a re-architecture of messaging/queuing: either outside the database (SQS/Lambda) or as a `SKIP LOCKED` queue table inside it.
- Recommended target pattern: Amazon SQS for queues + AWS Lambda for message processing, optionally DB Links for cross-database reads.
- Moving messaging out of the DB into Lambda/SQS reduces database load and cost.
- Consider Database Mail page for related notification scenarios.
- Use Amazon SQS FIFO queues when Service Broker's in-order, exactly-once delivery per conversation matters; standard SQS queues are at-least-once and unordered.
