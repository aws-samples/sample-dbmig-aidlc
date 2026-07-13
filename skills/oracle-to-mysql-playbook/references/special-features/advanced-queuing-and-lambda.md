# Oracle Advanced Queuing and MySQL Integration with Lambda

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.lambda.html

**Conversion category:** Manual (one-star feature compatibility; no automation)
**SCT automation:** N/A

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
CALL mysql.lambda_async(
  'arn:aws:lambda:us-west-2:123456789012:function:my_function',
  '{"input1":"value"}');
```

## Conversion notes

- There is no direct equivalent to Oracle AQ in Aurora MySQL; the recommended replacement is a combination of AWS Lambda + Amazon SQS (queuing) and/or Amazon SNS (notifications).
- Queue producer/consumer logic implemented in PL/SQL via `oracle.jdbc.aq` must be re-architected as application/Lambda code.
- Aurora MySQL must be granted IAM permissions to invoke Lambda.
- See the playbook "Amazon Simple Notification Service" topic for end-to-end examples.
