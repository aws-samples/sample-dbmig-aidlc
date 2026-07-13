# Transparent Data Encryption (TDE)

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.security.transparentdataencryption.html

**Conversion category:** Assisted (four-star compatibility — storage-level encryption managed by Amazon RDS)
**SCT automation:** N/A

## SQL Server

Transparent Data Encryption (TDE) protects data at rest in case an attacker obtains the physical media containing the database files. It requires no application changes and is transparent to users — the storage engine encrypts/decrypts data on the fly. Data is not encrypted in memory or on the network. TDE can be turned on/off per database.

TDE uses a Database Encryption Key (DEK) stored in the database boot record (so it is available during recovery). The DEK is a symmetric key signed with a server certificate from the master system database. Security compliance laws often require TDE for data at rest.

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

## PostgreSQL

Aurora PostgreSQL provides encryption at rest for new database instances via Amazon RDS. When enabled, RDS automatically encrypts server storage, automated backups, read replicas, and snapshots using AES-256. Keys are managed through IAM/AWS KMS. For full control, you manage the key yourself; you cannot delete, revoke, or rotate AWS-provisioned default keys.

This is configured at the infrastructure level (RDS console / KMS), not through SQL DDL.

**Enable encryption:** In the database settings, enable encryption and choose a master key — the default account key or a specific key by IAM KMS ARN (your account or another account).

**Create a customer-managed key:** In KMS, choose **Customer managed keys** → create a new key → choose key type and key material origin → set alias/description → define key administrative permissions → assign the key to the relevant users who interact with Aurora → review/edit the key policy → finish. Then set the master encryption key on the instance using the key ARN and launch.

Limitations of RDS encrypted instances:

- Encryption can only be enabled **at instance creation time**, not afterward. To encrypt an existing database: snapshot it → create an encrypted copy of the snapshot → restore from the encrypted snapshot.
- Encrypted instances cannot be modified to disable encryption.
- Encrypted read replicas must use the same key as the source instance.
- An unencrypted backup/snapshot cannot be restored to an encrypted instance.
- KMS keys are region-specific; copying an encrypted snapshot across regions requires the destination region's KMS key identifier.

> Note: Disabling the key for an encrypted instance prevents all reads/writes. If RDS encounters an instance encrypted by a key it cannot access, it puts the instance into a terminal state — the instance becomes unavailable and its current state cannot be recovered. To restore, re-enable access to the key for RDS and restore from a backup.

## Conversion notes

- Functionally equivalent goal (encryption at rest, transparent to applications) but a completely different implementation model: SQL Server TDE is managed in-database via SQL DDL (master key → certificate → DEK → `ALTER DATABASE ... SET ENCRYPTION ON`), whereas Aurora PostgreSQL encryption is **storage-level, managed by Amazon RDS + KMS** with no SQL DDL.
- There is no per-database TDE toggle — encryption applies to the whole RDS/Aurora instance and must be decided at creation time.
- Plan key management up front: choose AWS-managed default key vs customer-managed KMS key (CMK) based on your control/rotation requirements.
- To migrate an existing unencrypted instance to encrypted, use the snapshot → encrypted-copy → restore workflow.
- No SQL Server certificate/key migration is needed — drop the TDE DDL and configure RDS encryption + KMS instead.
