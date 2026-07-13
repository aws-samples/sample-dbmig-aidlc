# Service Broker

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.tsql.servicebroker.html

**Conversion category:** Manual (no feature compatibility, no automation)
**SCT automation:** No automation — SCT action code index: Service Broker

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

## Conversion notes
- No native equivalent — migration requires a full re-architecture of messaging/queuing outside the database.
- Recommended target pattern: Amazon SQS for queues + AWS Lambda for message processing, optionally DB Links for cross-database reads.
- Moving messaging out of the DB into Lambda/SQS reduces database load and cost.
- Consider Database Mail page for related notification scenarios.
