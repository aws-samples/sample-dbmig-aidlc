# UTL_MAIL / UTL_SMTP and SNS

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.sql.mail.html

**Conversion category:** Manual (★★ feature compatibility, no automation)
**SCT automation:** N/A — use Lambda integration.

## Oracle

### UTL_MAIL
Sends email, supports attachments (preferred over `UTL_SMTP` in most cases).

```sql
-- Install mail packages
@{ORACLE_HOME}/rdbms/admin/utlmail.sql
@{ORACLE_HOME}/rdbms/admin/prvtmail.plb

-- Configure SMTP server
ALTER SYSTEM SET smtp_out_server = 'smtp.domain.com' SCOPE=BOTH;

-- Send
exec utl_mail.send('Sender@example.com', 'recipient@example.com', NULL, NULL,
  'This is the subject', 'This is the message body', NULL, 3, NULL);
```

### UTL_SMTP
Lower-level email (useful for DB event alerts), no attachment support. Procedures: `OPEN_CONNECTION`, `HELO`, `MAIL`, `RCPT`, `DATA`, `QUIT`.

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

## MySQL

Aurora MySQL cannot configure engine alerts directly. For **database/instance event notifications**, use Amazon RDS Event Notifications backed by **Amazon SNS** (email, SMS, HTTP endpoints). Events are grouped into categories; you subscribe to categories (not individual events) for DB instances, clusters, snapshots, security groups, and parameter groups. Subscriptions are identified by an SNS topic ARN. Note: some Aurora events occur at cluster (not instance) level.

Create an Event Notification Subscription (RDS console): RDS → **Events** → **Event subscriptions** → **Create event subscription** → set Name, Target (ARN or new email topic), event source and categories → **Create**.

For **application email** from within the database:
- Prefer a dedicated email framework outside the DB.
- If email-generating code must live in the DB, use a **queue table**: replace `UTL_SMTP`/`UTL_MAIL` calls with an `INSERT` into the queue; an external app polls the queue, sends mail, and updates status. Messages can be populated from query results (like the `UTL_*` query option).
- The only way to send email directly from Aurora MySQL is **AWS Lambda integration** (invoke a Lambda from the DB cluster).

## Conversion notes
- For DB monitoring/alerting: map `UTL_MAIL`/`UTL_SMTP` event notifications to **Amazon SNS** via RDS Event Notifications.
- For transactional/application email: use a **queue table + external worker** or **AWS Lambda integration** (`CALL mysql.lambda_async(...)` / native Lambda invocation).
- No in-database SMTP client exists — all approaches move email-sending outside the database engine.
- Attachments (supported by `UTL_MAIL`) require an external sender (Lambda + SES, etc.).
