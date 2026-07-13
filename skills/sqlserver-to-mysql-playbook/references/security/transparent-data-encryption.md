# Transparent Data Encryption (TDE)

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.security.transparentdataencryption.html

**Conversion category:** Manual (configuration at instance-creation time)
**SCT automation:** N/A (four-star feature compatibility; enable encryption when creating the database instance)

## SQL Server

TDE protects data at-rest in case an attacker obtains the physical media containing database files. It requires no application changes and is transparent to users — the storage engine encrypts/decrypts data on-the-fly. Data is **not** encrypted while in memory or on the network. TDE can be toggled per-database.

TDE uses a Database Encryption Key (DEK) stored in the database boot record (available during recovery). The DEK is a symmetric key signed with a server certificate from the primary system database. Many security compliance laws require TDE for data at rest.

Example — enable TDE for a database:

```sql
-- Create a master key and certificate
USE master;
CREATE MASTER KEY ENCRYPTION BY PASSWORD = '<REPLACE_WITH_STRONG_PASSWORD>';
CREATE CERTIFICATE TDECert WITH SUBJECT = 'TDE Certificate';

-- Create a database encryption key
USE MyDatabase;
CREATE DATABASE ENCRYPTION KEY
WITH ALGORITHM = AES_128
ENCRYPTION BY SERVER CERTIFICATE TDECert;

-- Enable TDE
ALTER DATABASE MyDatabase SET ENCRYPTION ON;
```

## MySQL

Aurora MySQL provides encryption of data at rest for **new** database instances. When enabled, Amazon RDS automatically encrypts the database server storage, automated backups, read replicas, and snapshots using AES-256.

Keys for encrypted instances are managed in IAM via AWS KMS. To fully control a key you must manage it yourself; you can't delete, revoke, or rotate default AWS KMS keys.

Limitations of Amazon RDS encrypted instances:
- Encryption can only be enabled at instance **creation**, not afterward. To encrypt an existing database: take a snapshot, create an encrypted copy of the snapshot, then restore from the encrypted snapshot.
- Encrypted instances can't be modified to turn off encryption.
- Encrypted read replicas must use the same key as the source instance.
- An unencrypted backup/snapshot can't be restored to an encrypted instance.
- KMS keys are region-specific; copying an encrypted snapshot cross-region requires the destination region's KMS key identifier.

> Disabling the key for an encrypted instance prevents all reads/writes. If RDS encounters an instance encrypted with an inaccessible key, it puts the instance into a terminal state — the instance becomes unavailable and its current state can't be recovered. To restore, re-enable key access for RDS and restore from a backup.

Table-level encryption (MySQL 8) can be managed globally:
- `default_table_encryption` defines the encryption default for newly created schemas and general tablespaces.
- A schema's default can be set with the `DEFAULT ENCRYPTION` clause at `CREATE SCHEMA`.
- A table inherits the encryption of its schema/general tablespace by default.
- Enforce defaults by enabling `table_encryption_privilege_check`. The check fires when creating/altering a schema, general tablespace, or table with a setting that differs from the relevant default.
- The `TABLE_ENCRYPTION_ADMIN` privilege permits overriding defaults when the check is enabled.

Creating an encryption key (AWS KMS):
1. In KMS choose **Customer managed keys** and create a new key.
2. Choose relevant options → **Next**.
3. Define an alias (the key name) → **Next**.
4. Skip **Define Key Administrative Permissions** → **Next**.
5. Assign the key to the users who will interact with Aurora.
6. Review the key ARN and account, then **Finish** — the key is now listed under customer managed keys.

Then set the master encryption key (by ARN or from the list) during instance creation. Encryption can only be enabled at instance creation. You can select the account's default key or specify a key by IAM KMS ARN from your account or another account.

## Conversion notes
- No direct SQL/DDL equivalent. SQL Server's per-database TDE (master key + certificate + DEK + `ALTER DATABASE ... SET ENCRYPTION ON`) is replaced by **Amazon RDS/Aurora storage-level encryption configured at instance creation**, using AWS KMS keys — not SQL statements.
- Encryption must be decided at instance-creation time; you cannot enable it later in place (use the snapshot → encrypted-copy → restore path).
- Both approaches encrypt at rest only (not in memory or on the network).
- For table-level granularity, MySQL 8 offers `default_table_encryption` / `DEFAULT ENCRYPTION` / `table_encryption_privilege_check`, but the primary mechanism for Aurora is whole-instance KMS encryption.
- Plan KMS key ownership/region carefully; losing key access puts the instance in an unrecoverable terminal state.
