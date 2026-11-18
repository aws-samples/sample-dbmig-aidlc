# Database mail features

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.databasemail.html

**Conversion category:** N/A (one-star feature compatibility)
**SCT automation:** N/A (SCT action code index: SQL Server Mail)

> **Reviewed for Aurora PostgreSQL 18** (validated on 18.6, 2026-10-29): fixed sample bugs (table name, handler), EventBridge Scheduler, `aws_lambda` push pattern with SES API, transactional caveat, query-result attachments.

> **Content security review** (2026-11-18): the walkthrough now sends through the SES API with the Lambda execution role (no SMTP user); SES SMTP is a labelled fallback with long-lived credentials.

Key difference: Use AWS Lambda integration.

## SQL Server

Database Mail is an email client solution for sending messages directly from SQL Server (admin messages such as alerts/logs/status, and application messages). It is off by default.

Features:
- Sends via SMTP; the engine runs asynchronously in a separate process.
- Supports multiple SMTP servers for redundancy and Windows Server Failover Cluster.
- Multi-profile support with failover accounts; security enforced via `msdb` roles.
- Attachment size caps, deny-list of attachment file types, full auditing with retention, plain text and HTML messages.

Architecture: Built on Service Broker queues. `sp_send_dbmail` inserts a row into the mail queue, triggering `DatabaseMail.exe`, which reads the message and sends to SMTP. SMTP acknowledgment/rejection inserts a status row, triggering a status-update procedure. The legacy `xp_sendmail` / SQL Mail framework was deprecated in SQL Server 2008 R2.

Syntax (abbreviated):

```sql
EXECUTE sp_send_dbmail
    [@profile_name =] '<Profile Name>',
    [@recipients =] '<Recipients>',
    [@subject =] '<Subject>',
    [@body =] '<Message Body>',
    [@query =] '<SQL Query>',
    [@attach_query_result_as_file =] <0|1> ...
```

Example — set up and send:

```sql
-- Create a Database Mail account
EXECUTE msdb.dbo.sysmail_add_account_sp
    @account_name = 'MailAccount1',
    @description = 'Mail account for testing DB Mail',
    @email_address = 'address@example.com',
    @replyto_address = 'replyaddress@example.com',
    @display_name = 'Mailer for registration messages',
    @mailserver_name = 'smtp.example.com';

-- Create a profile
EXECUTE msdb.dbo.sysmail_add_profile_sp
    @profile_name = 'MailAccount1 Profile',
    @description = 'Mail Profile for testing DB Mail';

-- Associate the account with the profile
EXECUTE msdb.dbo.sysmail_add_profileaccount_sp
    @profile_name = 'MailAccount1 Profile',
    @account_name = 'MailAccount1',
    @sequence_number = 1;

-- Grant the profile to a principal
EXECUTE msdb.dbo.sysmail_add_principalprofile_sp
    @profile_name = 'MailAccount1 Profile',
    @principal_name = 'ApplicationUser',
    @is_default = 1;

-- Send a message
EXEC msdb.dbo.sp_send_dbmail
    @profile_name = 'MailAccount1 Profile',
    @recipients = 'recipient@example.com',
    @query = 'SELECT * FROM fn_WeeklySalesReport(GETDATE())',
    @subject = 'Weekly Sales Report',
    @attach_query_result_as_file = 1;
```

## PostgreSQL

Aurora PostgreSQL has no native support for sending email from the database. For alerting, use Event Notification Subscriptions (see Alerting). To send arbitrary email, use AWS Lambda integration with Amazon SES.

Example walkthrough — send email from Aurora PostgreSQL via Lambda + SES. The Lambda sends
through the **SES API with its execution role**, so no mail credentials are created or stored:
1. Verify a sending identity in Amazon SES (an email address or a domain). In the SES sandbox,
   also verify the recipients, or request production access.
2. Create a table to queue messages:

   ```sql
   CREATE TABLE mails (title varchar(600), body varchar(600), recipients varchar(600));
   ```
3. Create a Lambda function (Author from scratch, Python runtime). Give its execution role only
   what it needs: `ses:SendEmail` on the verified identity, and `rds-db:connect` for the
   database user (IAM database authentication):

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {"Effect": "Allow", "Action": "ses:SendEmail",
        "Resource": "arn:aws:ses:<region>:<account-id>:identity/sender@example.com"},
       {"Effect": "Allow", "Action": "rds-db:connect",
        "Resource": "arn:aws:rds-db:<region>:<account-id>:dbuser:<cluster-resource-id>/mail_sender"}
     ]
   }
   ```
4. Provide `main.py` and `db_util.py` (uses `psycopg2` to read the queued rows and the SES API
   to send them, then deletes the sent rows).

   `main.py`:

   ```python
   #!/usr/bin/python
   import sys, logging, psycopg2
   from db_util import make_conn, fetch_data

   def lambda_handler(event, context):
       query_cmd = "select * from mails"
       conn = make_conn()
       result = fetch_data(conn, query_cmd)
       conn.close()
       return result
   ```

   `db_util.py` (key parts):

   ```python
   #!/usr/bin/python
   # SECURITY: no credentials are hardcoded or stored anywhere.
   #  - Aurora PostgreSQL: IAM database authentication — make_conn() mints a short-lived auth
   #    token at runtime (there is no DB password). The DB role is created WITH LOGIN and
   #    granted rds_iam.
   #  - Amazon SES: the SES API is called with the Lambda execution role (ses:SendEmail on the
   #    verified identity), so there is no SMTP user or password.
   import os, boto3, psycopg2

   DB_HOST = os.environ['DB_HOST']            # cluster endpoint (non-secret config)
   DB_PORT = int(os.environ.get('DB_PORT', '5432'))
   DB_NAME = os.environ['DB_NAME']
   DB_USER = os.environ['DB_USER']            # DB role created WITH LOGIN + rds_iam
   REGION  = os.environ['AWS_REGION']
   SENDER  = os.environ['SENDER']             # SES-verified sending identity
   ses = boto3.client('sesv2')

   def sendEmail(recp, sub, message):
       try:
           ses.send_email(
               FromEmailAddress=SENDER,
               Destination={'ToAddresses': [recp]},
               Content={'Simple': {'Subject': {'Data': sub},
                                   'Body': {'Text': {'Data': message},
                                            'Html': {'Data': "<html>...%s...</html>" % message}}}})
       except Exception as e:
           print("Error: ", e)

   def make_conn():
       # IAM database authentication: generate a short-lived auth token (valid ~15 min)
       # instead of using a stored password; SSL is required for IAM-authenticated connections.
       token = boto3.client('rds').generate_db_auth_token(
           DBHostname=DB_HOST, Port=DB_PORT, DBUsername=DB_USER, Region=REGION)
       try:
           return psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                                    user=DB_USER, password=token, sslmode='require')
       except Exception as e:
           print("Unable to connect to the database:", e)
           return None

   def fetch_data(conn, query):
       result = []
       cursor = conn.cursor()
       cursor.execute(query)
       for line in cursor.fetchall():
           sendEmail(line[2], line[0], line[1])
           result.append(line)
       cursor.execute('delete from mails')
       cursor.execute('commit')
       return result
   ```

   Note: the Lambda deletes the contents of the mails table after sending.
5. Package `main.py` + `db_util.py` (with a `psycopg2-binary`/`psycopg` Lambda layer) into a ZIP, upload, set Handler to `main.lambda_handler`, and set `DB_HOST`, `DB_NAME`, `DB_USER` and `SENDER`.
6. Test, then schedule with **Amazon EventBridge Scheduler** (e.g., every minute using a rate/cron expression — you pay per invocation), or call `aws_lambda.invoke` from `pg_cron`.

**Fallback: SES SMTP.** Use SMTP only when the sending code must be an SMTP client. SES SMTP
credentials belong to an IAM user and are **long-lived**: create them only for this purpose,
store them in AWS Secrets Manager (the Lambda reads them at send time with
`secretsmanager:GetSecretValue` on that one secret), never in code or environment variables, and
rotate them on a schedule. See [Obtaining Amazon SES SMTP credentials](https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html).

### Simpler alternative on Aurora PostgreSQL 18: push instead of poll
`sp_send_dbmail` can map to a direct asynchronous Lambda call from PL/pgSQL with the `aws_lambda` extension (2.1 on Aurora 18). The Lambda sends through the **SES API** with its IAM role, so no SMTP secret is needed:
```sql
CREATE EXTENSION IF NOT EXISTS aws_lambda CASCADE;
SELECT * FROM aws_lambda.invoke(
  aws_commons.create_lambda_function_arn('send-mail', 'us-west-2'),
  json_build_object('to', 'recipient@example.com', 'subject', 'Weekly Sales Report',
                    'query_result', (SELECT json_agg(r) FROM fn_weekly_sales_report(now()) r)),
  'Event');
```
The cluster needs an IAM role with the `Lambda` feature (`aws rds add-role-to-db-cluster --feature-name Lambda`). The call is **not transactional**: a rolled-back transaction still sends the mail. Use the queue table when mail must follow commit. `@attach_query_result_as_file` → build the CSV in Lambda, or `aws_s3.query_export_to_s3` + a presigned link in the mail.

## Conversion notes

- No native database mail in Aurora PostgreSQL — replace `sp_send_dbmail` with AWS Lambda + Amazon SES.
- For alert-style notifications prefer Amazon RDS event notifications + Amazon SNS rather than custom mail (see Alerting).
- AWS service replacements: AWS Lambda (logic), Amazon SES (API with the Lambda role; SMTP only as a fallback), Amazon EventBridge Scheduler (scheduling), `aws_lambda.invoke` (push from SQL).
- The queue-table + scheduled-Lambda pattern emulates Database Mail's asynchronous send queue.
