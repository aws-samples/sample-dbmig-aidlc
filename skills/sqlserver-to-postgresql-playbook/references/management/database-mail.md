# Database mail features

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.management.databasemail.html

**Conversion category:** N/A (one-star feature compatibility)
**SCT automation:** N/A (SCT action code index: SQL Server Mail)

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

Example walkthrough — send email from Aurora PostgreSQL via Lambda + SES:
1. Configure Amazon SES; create SMTP credentials (**SES → SMTP Settings → Create My SMTP Credentials**) and copy the SMTP server name.
2. Enter the IAM user name for the SMTP user, choose **Create**, and save the credentials (not retrievable later).
3. Verify a sender email address (**SES → Email Addresses → Verify a New Email Address**).
4. Create a table to queue messages:

   ```sql
   CREATE TABLE emails (title varchar(600), body varchar(600), recipients varchar(600));
   ```
5. Create a Lambda function (Author from scratch, Python runtime, role with correct permissions).
6. Provide `main.py` and `db_util.py` (uses `psycopg2` to read the queued rows and `smtplib` to send via SES SMTP, then deletes the sent rows).

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
   import psycopg2, smtplib, email.utils
   from email.mime.multipart import MIMEMultipart
   from email.mime.text import MIMEText

   # SECURITY: no database credentials are hardcoded or stored anywhere.
   #  - Aurora PostgreSQL: use IAM database authentication — make_conn() below mints a
   #    short-lived auth token at runtime (there is no DB password). The Lambda execution role
   #    needs rds-db:connect on the db-user resource ARN, and the DB role is created WITH LOGIN
   #    and granted rds_iam.
   #  - SES SMTP: SES SMTP requires a username/password, so keep ONLY that secret in Secrets
   #    Manager and read it at send time (least-privilege secretsmanager:GetSecretValue on it).
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
       SENDER = 'sender@example.com'; SENDERNAME = 'Lambda'   # SES-verified sending identity
       RECIPIENT = recp
       USERNAME_SMTP = smtp['username']; PASSWORD_SMTP = smtp['password']
       HOST = smtp['host']; PORT = 587
       msg = MIMEMultipart('alternative')
       msg['Subject'] = sub
       msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
       msg['To'] = RECIPIENT
       msg.attach(MIMEText("Amazon SES Test", 'plain'))
       msg.attach(MIMEText("<html>...%s...</html>" % message, 'html'))
       try:
           server = smtplib.SMTP(HOST, PORT)
           server.ehlo(); server.starttls(); server.ehlo()
           server.login(USERNAME_SMTP, PASSWORD_SMTP)
           server.sendmail(SENDER, RECIPIENT, msg.as_string())
           server.close()
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
7. Package `main.py` + `db_util.py` (with the `psycopg2` dependency) into a ZIP, upload, set Handler to `mail.lambda_handler`.
8. Test, then schedule via Amazon CloudWatch (e.g., every minute using a rate/cron expression — you pay per invocation).

## Conversion notes

- No native database mail in Aurora PostgreSQL — replace `sp_send_dbmail` with AWS Lambda + Amazon SES.
- For alert-style notifications prefer Amazon RDS event notifications + Amazon SNS rather than custom mail (see Alerting).
- AWS service replacements: AWS Lambda (logic), Amazon SES (SMTP delivery), Amazon CloudWatch Events (scheduling).
- The queue-table + scheduled-Lambda pattern emulates Database Mail's asynchronous send queue.
