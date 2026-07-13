# UTL_MAIL / UTL_SMTP and Scheduled Lambda with Amazon SES

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.sql.mail.html

**Conversion category:** Manual (Three-star feature compatibility, no automation; redesign using Lambda + Amazon SES integration)
**SCT automation:** No automation; SCT action code index N/A

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

1. Configure Amazon SES: create SMTP credentials (SES → SMTP Settings → Create My SMTP Credentials), note SMTP server name and credentials (not retrievable later). Verify sender (and, in sandbox, recipient) email addresses.
2. Create a table to queue messages:
   ```sql
   CREATE TABLE emails (title varchar(600), body varchar(600), recipients varchar(600));
   ```
3. Create a Lambda function (e.g., Python) that connects to the DB, reads queued mails, sends via SES SMTP, then clears the table.

`main.py` (handler):

```python
#!/usr/bin/python
import sys, logging, psycopg2
from db_util import make_conn, fetch_data

def lambda_handler(event, context):
    query_cmd = "select * from mails"
    print query_cmd
    conn = make_conn()
    result = fetch_data(conn, query_cmd)
    conn.close()
    return result
```

`db_util.py` (DB connect + SES SMTP send) — key parts:

```python
# SECURITY: no database credentials are hardcoded or stored anywhere.
#  - Aurora PostgreSQL: use IAM database authentication — make_conn() below mints a short-lived
#    auth token at runtime (there is no DB password). The Lambda execution role needs
#    rds-db:connect on the db-user resource ARN, and the DB role is created WITH LOGIN + rds_iam.
#  - SES SMTP: SES SMTP requires a username/password, so keep ONLY that secret in Secrets Manager
#    and read it at send time (least-privilege secretsmanager:GetSecretValue on that secret).
import os, json, boto3

DB_HOST = os.environ['DB_HOST']            # cluster endpoint (non-secret config)
DB_PORT = int(os.environ.get('DB_PORT', '5432'))
DB_NAME = os.environ['DB_NAME']
DB_USER = os.environ['DB_USER']            # DB role created WITH LOGIN + rds_iam
REGION  = os.environ['AWS_REGION']
SMTP_SECRET_ID = os.environ['SMTP_SECRET_ID']

def sendEmail(recp, sub, message):
    smtp = json.loads(boto3.client('secretsmanager')
                      .get_secret_value(SecretId=SMTP_SECRET_ID)['SecretString'])
    SENDER = 'sender@example.com'   # an SES-verified sending identity
    SENDERNAME = 'Lambda'
    RECIPIENT = recp
    USERNAME_SMTP = smtp['username']
    PASSWORD_SMTP = smtp['password']
    HOST = smtp['host']                  # SES SMTP endpoint, e.g. email-smtp.us-west-2.amazonaws.com
    PORT = 587
    # build multipart/alternative message (text + html) ...
    server = smtplib.SMTP(HOST, PORT)
    server.ehlo(); server.starttls(); server.ehlo()
    server.login(USERNAME_SMTP, PASSWORD_SMTP)
    server.sendmail(SENDER, RECIPIENT, msg.as_string())
    server.close()

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

4. Package `main.py` + `db_util.py` (with the `psycopg2` GitHub project) into a ZIP, upload to Lambda, set Handler to `mail.lambda_handler`.
5. Schedule with an Amazon CloudWatch Events rule (e.g., every minute via a rate/cron expression). Note: you pay per Lambda execution.

## Conversion notes

- No in-database email — `UTL_MAIL`/`UTL_SMTP` calls must be removed and replaced with an external send mechanism.
- Map the procedural send (`utl_mail.send` / `UTL_SMTP.*`) to: enqueue a row in an `emails`/`mails` table, then have a scheduled Lambda send it via SES SMTP.
- For simple operational alerts (not arbitrary email), prefer RDS Event Notification Subscriptions or SNS.
- Secure SMTP/DB credentials (use Secrets Manager / IAM rather than hardcoding as in the sample).
- SES sandbox requires verified sender and recipient addresses; request production access to send to arbitrary recipients.
