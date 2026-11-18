# UTL_MAIL / UTL_SMTP and Scheduled Lambda with Amazon SES

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.mail.html

**Conversion category:** Manual (Three-star feature compatibility, no automation; redesign using Lambda + Amazon SES integration)
**SCT automation:** No automation; SCT action code index N/A

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): fixed sample bugs (table name, Python 3 `print`, handler name), EventBridge Scheduler, push pattern with `aws_lambda.invoke` + SES API (no SMTP secret), non-transactional caveat.

> **Content security review** (2026-11-18): the Lambda + SES pattern now sends through the SES API with the Lambda execution role (no SMTP user); SES SMTP is a labelled fallback with long-lived credentials.

## Oracle

### UTL_MAIL

Sends email from the database; supports attachments (preferred over `UTL_SMTP` in most cases).

```sql
-- Install packages
@{ORACLE_HOME}/rdbms/admin/utlmail.sql
@{ORACLE_HOME}/rdbms/admin/prvtmail.plb

-- Configure outgoing SMTP server
ALTER SYSTEM SET smtp_out_server = 'smtp.domain.com' SCOPE=BOTH;

-- Send
exec utl_mail.send('Sender@example.com', 'recipient@example.com', NULL, NULL,
  'This is the subject', 'This is the message body', NULL, 3, NULL);
```

### UTL_SMTP

More complex, no attachment support. Useful for DB-event alerts. Procedures: `OPEN_CONNECTION`, `HELO`, `MAIL`, `RCPT`, `DATA`, `QUIT`.

```sql
DECLARE
  smtpconn utl_smtp.connection;
BEGIN
  smtpconn := UTL_SMTP.OPEN_CONNECTION('smtp.example.com', 25);
  UTL_SMTP.HELO(smtpconn, 'smtp.example.com');
  UTL_SMTP.MAIL(smtpconn, 'sender@example.com');
  UTL_SMTP.RCPT(smtpconn, 'recipient@example.com');
  UTL_SMTP.DATA(smtpconn, 'Message body');
  UTL_SMTP.QUIT(smtpconn);
END;
/
```

## PostgreSQL

Amazon Aurora PostgreSQL has **no native in-database email**. Options:
- For alerting, use RDS/Aurora **Event Notification Subscriptions** to email operators.
- To send email from the database, use **AWS Lambda integration + Amazon SES**.

### Lambda + SES pattern

1. Verify a sending identity in Amazon SES (an email address or a domain); in the SES sandbox, also verify the recipients. The Lambda sends through the **SES API with its execution role**, so no mail credentials are created or stored. The role needs `ses:SendEmail` on the verified identity's ARN (`arn:aws:ses:<region>:<account-id>:identity/sender@example.com`) and `rds-db:connect` for the database user.
2. Create a table to queue messages:
   ```sql
   CREATE TABLE mails (title varchar(600), body varchar(600), recipients varchar(600));
   ```
3. Create a Lambda function (e.g., Python) that connects to the DB, reads queued mails, sends them with the SES API, then clears the table.

`main.py` (handler):

```python
#!/usr/bin/python
import sys, logging, psycopg2
from db_util import make_conn, fetch_data

def lambda_handler(event, context):
    query_cmd = "select * from mails"
    print(query_cmd)
    conn = make_conn()
    result = fetch_data(conn, query_cmd)
    conn.close()
    return result
```

`db_util.py` (DB connect + SES API send) — key parts:

```python
# SECURITY: no credentials are hardcoded or stored anywhere.
#  - Aurora PostgreSQL: use IAM database authentication — make_conn() below mints a short-lived
#    auth token at runtime (there is no DB password). The Lambda execution role needs
#    rds-db:connect on the db-user resource ARN, and the DB role is created WITH LOGIN + rds_iam.
#  - Amazon SES: the SES API is called with the Lambda execution role (ses:SendEmail on the
#    verified identity), so there is no SMTP user or password.
import os, boto3, psycopg2

DB_HOST = os.environ['DB_HOST']            # cluster endpoint (non-secret config)
DB_PORT = int(os.environ.get('DB_PORT', '5432'))
DB_NAME = os.environ['DB_NAME']
DB_USER = os.environ['DB_USER']            # DB role created WITH LOGIN + rds_iam
REGION  = os.environ['AWS_REGION']
SENDER  = os.environ['SENDER']             # an SES-verified sending identity
ses = boto3.client('sesv2')

def sendEmail(recp, sub, message):
    ses.send_email(
        FromEmailAddress=SENDER,
        Destination={'ToAddresses': [recp]},
        Content={'Simple': {'Subject': {'Data': sub},
                            'Body': {'Text': {'Data': message}}}})

def make_conn():
    # IAM database authentication: mint a short-lived auth token (valid ~15 min) instead of a
    # stored password; SSL is required for IAM-authenticated connections.
    token = boto3.client('rds').generate_db_auth_token(
        DBHostname=DB_HOST, Port=DB_PORT, DBUsername=DB_USER, Region=REGION)
    return psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                            user=DB_USER, password=token, sslmode='require')

def fetch_data(conn, query, params=None):
    # SECURITY: `query` must be a trusted, static statement (as used here). Never build it
    # from user-controlled input. To filter rows, pass bound parameters — never string-format
    # them into the SQL, e.g.:
    #     fetch_data(conn, "SELECT * FROM mails WHERE status = %s", (status,))
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    raw = cursor.fetchall()
    for line in raw:
        sendEmail(line[2], line[0], line[1])   # recipients, title, body
    cursor.execute('delete from mails')
    cursor.execute('commit')
    return raw
```

> Note: the Lambda deletes the contents of the mails table after sending.

**Fallback: SES SMTP.** Use SMTP only when the sending code must be an SMTP client. SES SMTP
credentials belong to an IAM user and are **long-lived**: create them only for this purpose,
store them in AWS Secrets Manager (read at send time with `secretsmanager:GetSecretValue` on that
one secret), never in code or environment variables, and rotate them on a schedule. See
[Obtaining Amazon SES SMTP credentials](https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html).

4. Package `main.py` + `db_util.py` (with a `psycopg2-binary` or `psycopg` Lambda layer) into a ZIP, upload to Lambda, set Handler to `main.lambda_handler`.
5. Schedule with **Amazon EventBridge Scheduler** (the successor to CloudWatch Events rules), e.g. every minute via a rate/cron expression, or with `pg_cron` calling `aws_lambda.invoke`. Note: you pay per Lambda execution.

### Simpler alternative on Aurora PostgreSQL 18: push instead of poll

Instead of a polling Lambda, call Lambda **from the database** with the `aws_lambda` extension (2.1 on Aurora 18; the cluster needs an IAM role with the `Lambda` feature and `lambda:InvokeFunction`). Have the Lambda send through the **SES API** (`sesv2.send_email` with its IAM role), which removes the SMTP password entirely:

```sql
CREATE EXTENSION IF NOT EXISTS aws_lambda CASCADE;
-- utl_mail.send(sender, recipients, cc, bcc, subject, message) →
SELECT * FROM aws_lambda.invoke(
  aws_commons.create_lambda_function_arn('send-mail', 'us-west-2'),
  json_build_object('to', 'recipient@example.com', 'subject', 'This is the subject',
                    'body', 'This is the message body'),
  'Event');                              -- asynchronous: does not wait for SES
```

Calling Lambda inside a transaction is **not transactional**: if the transaction rolls back, the mail is still sent. When mail must only go out after commit, keep the queue-table pattern (insert in the transaction, send after commit).

## Conversion notes

- No in-database email — `UTL_MAIL`/`UTL_SMTP` calls must be removed and replaced with an external send mechanism.
- Map the procedural send (`utl_mail.send` / `UTL_SMTP.*`) to: enqueue a row in an `emails`/`mails` table, then have a scheduled Lambda send it with the SES API.
- For simple operational alerts (not arbitrary email), prefer RDS Event Notification Subscriptions or SNS.
- Secure credentials: IAM database authentication for the Lambda's DB connection, and the SES API with the Lambda's IAM role. Only if SMTP is required: long-lived SMTP credentials in Secrets Manager, rotated.
- `aws_lambda.invoke` with `'Event'` (async) is the closest replacement for a direct `UTL_MAIL.SEND` call. The queue-table + scheduled Lambda pattern is the transactionally safe replacement.
- SES sandbox requires verified sender and recipient addresses; request production access to send to arbitrary recipients.
