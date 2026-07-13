# Database mail features

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.management.databasemail.html

**Conversion category:** Manual (One star feature compatibility)
**SCT automation:** No automation

## SQL Server

Database Mail is an email client solution for sending messages directly from SQL Server (server administration messages such as alerts/logs/status reports, and application messages such as registration confirmations). It is turned off by default.

Key features: uses secure SMTP; runs asynchronously in a separate process; supports multiple SMTP servers for redundancy; Windows Server Failover Cluster aware; multi-profile with failover accounts; role-based security in MSDB; attachment size caps and file-type deny lists; logging to SQL Server / Windows application log / MSDB system tables; auditing with retention; plain text and HTML.

**Architecture:** Built on Service Broker queue management. `sp_send_dbmail` inserts a row into the mail queue, which triggers DatabaseMail.exe to read and send via SMTP. SMTP acknowledgements/rejections insert a status row, triggering a status-update stored procedure. Attachments are recorded in system tables.

The legacy SQL Mail framework (`xp_sendmail`) was deprecated as of SQL Server 2008 R2 and replaced by Database Mail.

Syntax (`sp_send_dbmail`):

```sql
EXECUTE sp_send_dbmail
    [[,@profile_name =] '<Profile Name>']
    [,[,@recipients =] '<Recipients>']
    [,[,@copy_recipients =] '<CC Recipients>']
    [,[,@blind_copy_recipients =] '<BCC Recipients>']
    [,[,@from_address =] '<From Address>']
    [,[,@reply_to =] '<Reply-to Address>']
    [,[,@subject =] '<Subject>']
    [,[,@body =] '<Message Body>']
    [,[,@body_format =] '<Message Body Format>']
    ... (importance, sensitivity, file_attachments, query, etc.)
```

Examples:

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

-- Associate account with profile
EXECUTE msdb.dbo.sysmail_add_profileaccount_sp
    @profile_name = 'MailAccount1 Profile',
    @account_name = 'MailAccount1',
    @sequence_number = 1;

-- Grant profile access
EXECUTE msdb.dbo.sysmail_add_principalprofile_sp
    @profile_name = 'MailAccount1 Profile',
    @principal_name = 'ApplicationUser',
    @is_default = 1;

-- Send a message with a query result attached
EXEC msdb.dbo.sp_send_dbmail
    @profile_name = 'MailAccount1 Profile',
    @recipients = 'recipient@example.com',
    @query = 'SELECT * FROM fn_WeeklySalesReport(GETDATE())',
    @subject = 'Weekly Sales Report',
    @attach_query_result_as_file = 1;
```

## MySQL

Aurora MySQL doesn't natively support sending mail from the database.

- For **alerting**, use the event notification subscription feature (Amazon SNS) to email operators — see Alerting reference.
- For **application email**, use a dedicated email framework. If email-generating code must live in the database, use a **queue table**: replace each `sp_send_dbmail` call with an `INSERT` into the queue table, and design an external app to read the queue, send the email, and update status periodically.
- The only way to send email directly from the database is via **AWS Lambda integration** — see [Invoking a Lambda function from an Amazon Aurora MySQL DB cluster](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Integrating.Lambda.html).

## Conversion notes
- AWS service replacements: alerting email → **Amazon SNS**; direct DB-sent mail → **AWS Lambda integration**; application email → external mail service + **queue table** pattern.
- No SCT automation; all `sp_send_dbmail` usage must be rewritten.
- Replace `sp_send_dbmail` calls with INSERTs into a queue table consumed by an external process, or invoke Lambda for SMTP/SES delivery.
