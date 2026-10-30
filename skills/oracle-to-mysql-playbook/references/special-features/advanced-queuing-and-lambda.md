# Oracle Advanced Queuing and MySQL Integration with Lambda

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.lambda.html

**Conversion category:** Manual (one-star feature compatibility; no automation)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Replaced the removed mysql.lambda_async procedure with the native lambda_async/lambda_sync functions (verified on both versions), setup steps, SKIP LOCKED queue-table pattern, CDC options.

## Oracle

Oracle Advanced Queuing (AQ) provides database-integrated message queuing. It is based on Oracle Streams and stores messages in database tables, allocates them to service queues, and transmits them using Oracle Net Services, HTTP, and HTTPS.

Oracle exposes the `oracle.jdbc.aq` Java package as an interface to AQ:

- Classes:
  - `AQDequeueOptions` — options for the dequeue operation
  - `AQEnqueueOptions` — options for the enqueue operation
  - `AQFactory` — factory class that creates components such as agent or message properties
  - `AQNotificationEvent` — new message notifications
- Interfaces:
  - `AQAgent` — identity of a user, producer, or consumer of a message
  - `AQMessage` — an enqueued or dequeued message
  - `AQMessageProperties` — message properties such as correlation, sender, delay, expiration, recipients, priority, ordering
  - `AQNotificationListener` — listener for receiving AQ notification events
  - `AQNotificationRegistration` — registration to be notified when a new message is enqueued on a particular queue

## MySQL

Aurora MySQL has no native message-queuing feature. Instead, it provides built-in integration with AWS Lambda functions that can be called from within the database and interact with Amazon SNS and Amazon SQS. This gives an event-driven framework using AWS services in place of AQ.

Invoke a Lambda function with the Aurora MySQL native function:

```sql
-- Aurora MySQL 3 / 8.4: native functions (the mysql.lambda_async procedure no longer exists — verified)
SELECT lambda_async('arn:aws:lambda:us-west-2:123456789012:function:my_function',
                    '{"input1":"value"}');
SELECT lambda_sync('arn:aws:lambda:…:function:my_function', JSON_OBJECT('id', 42));  -- returns the response
```

Setup (verified on 3.13 and 8.4.8 — calls fail until this is done, naming `aws_default_lambda_role`): create an IAM role that allows `lambda:InvokeFunction`, associate it with the cluster, set `aws_default_lambda_role` in the DB cluster parameter group, and `GRANT AWS_LAMBDA_ACCESS TO user` (plus `SET DEFAULT ROLE`). The cluster needs a network path to the Lambda endpoint (NAT gateway or a Lambda VPC endpoint).

## Conversion notes

- There is no direct equivalent to Oracle AQ in Aurora MySQL; the recommended replacement is a combination of AWS Lambda + Amazon SQS (queuing) and/or Amazon SNS (notifications).
- Queue producer/consumer logic implemented in PL/SQL via `oracle.jdbc.aq` must be re-architected as application/Lambda code.
- Aurora MySQL must be granted IAM permissions to invoke Lambda.
- See the playbook "Amazon Simple Notification Service" topic for end-to-end examples.
- When messages must be transactional with the data (the main reason AQ is used), use a **queue table** consumed with `SELECT … FOR UPDATE SKIP LOCKED` (available on Aurora MySQL 3 / 8.4, verified) by workers, or by an event/Lambda that moves committed rows to SQS. A `lambda_async` call from a trigger runs even if the transaction later rolls back.
- For change-data streaming to consumers, binary-log CDC (AWS DMS, Debezium on MSK) or a zero-ETL integration replaces AQ propagation.
