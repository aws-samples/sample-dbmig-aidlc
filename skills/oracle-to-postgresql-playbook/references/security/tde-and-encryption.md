# Oracle Transparent Data Encryption and PostgreSQL Encryption

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.security.encryption.html

**Conversion category:** Manual (Two star feature compatibility — use Amazon Aurora Encryption)
**SCT automation:** N/A

## Oracle

Oracle data-at-rest encryption is called **Transparent Data Encryption (TDE)**. TDE encrypts data saved in tables or tablespaces and protects data stored on media (data at rest) if the media or data files are stolen. It works at the operating system level, and the database manages it automatically — no application/client changes are needed. TDE does **not** protect data in transit (use network encryption for that).

Key facts:
- The user configuring TDE needs the `ADMINISTER KEY MANAGEMENT` system privilege.
- Data can be encrypted at the **column level** or **tablespace level**.
- The encryption key managed in an external module is called the **TDE root encryption key**.
- There is one root key store per database.

**Configure the keystore location** in `sqlnet.ora` via `ENCRYPTION_WALLET_LOCATION`. The key file can live on a regular filesystem, be shared by multiple DBs, on an ASM filesystem, or in an ASM disk group:

```
ENCRYPTION_WALLET_LOCATION=
  (SOURCE=
    (METHOD=FILE)
      (METHOD_DATA=
        (DIRECTORY=+ASM_file_path_of_the_diskgroup)))
```

**Create software keystores** (types: password-based, auto-login, local auto-login). Create a password-based keystore connected as a user with `ADMINISTER KEY MANAGEMENT` or `SYSKM`:

```sql
sqlplus c##sec_admin as syskm
Enter password: password
Connected.

ADMINISTER KEY MANAGEMENT CREATE KEYSTORE '/etc/ORACLE/WALLETS/orcl' IDENTIFIED BY password;

keystore altered.
```

**Open the keystore** before any TDE root keys can be created or accessed (auto-login and local auto-login open automatically):

```sql
sqlplus c##sec_admin as syskm
Enter password: password
Connected.

ADMINISTER KEY MANAGEMENT SET KEYSTORE OPEN IDENTIFIED BY password;

keystore altered.
```

**Set the software root encryption key** (protects the TDE table keys and tablespace encryption keys; by default TDE generates it). Database must be open in `READ WRITE` mode:

```sql
sqlplus c##sec_admin as syskm
Enter password: password
Connected.

ADMINISTER KEY MANAGEMENT SET KEY IDENTIFIED BY keystore_password WITH BACKUP USING 'emp_key_backup';

keystore altered.
```

**Column-level encryption** supports these data types: `BINARY_DOUBLE`, `BINARY_FLOAT`, `CHAR`, `DATE`, `INTERVAL DAY TO SECOND`, `INTERVAL YEAR TO MONTH`, `NCHAR`, `NUMBER`, `NVARCHAR2`, `RAW` (legacy or extended), `TIMESTAMP` (incl. `WITH TIME ZONE` and `WITH LOCAL TIME ZONE`), `VARCHAR2` (legacy or extended).

Column encryption **cannot** be used with:
- Index types other than B-tree.
- Range scan search through an index.
- Synchronous change data capture.
- Transportable tablespaces.
- Columns used in foreign key constraints.

Create a table with an encrypted column:

```sql
CREATE TABLE employee (
  FIRST_NAME VARCHAR2(128),
  LAST_NAME VARCHAR2(128),
  EMP_ID NUMBER,
  SALARY NUMBER(6) ENCRYPT);
```

Change the encryption algorithm. `NO SALT` encrypts without salt; the `USING` clause defines the algorithm:

```sql
CREATE TABLE EMPLOYEE (
  FIRST_NAME VARCHAR2(128),
  LAST_NAME VARCHAR2(128),
  EMP_ID NUMBER ENCRYPT NO SALT,
  SALARY NUMBER(6) ENCRYPT USING '3DES168');
```

Rekey to change the algorithm, and stop encrypting a column:

```sql
ALTER TABLE EMPLOYEE REKEY USING 'SHA-1';

ALTER TABLE employee MODIFY (SALARY DECRYPT);
```

**Tablespace-level encryption** encrypts at the SQL layer, so the data-type and index restrictions of column encryption do not apply. Requires `COMPATIBLE` >= 11.2.0.0. You can only create a new encrypted tablespace, not modify an existing one:

```sql
sqlplus sec_admin@hrpdb
Enter password: password
Connected.

CREATE TABLESPACE encrypt_ts
DATAFILE '$ORACLE_HOME/dbs/encrypt_df.dbf' SIZE 1M
ENCRYPTION USING 'AES256'
DEFAULT STORAGE (ENCRYPT);

CREATE TABLESPACE securespace_2
DATAFILE '/home/user/oradata/secure01.dbf'
SIZE 150M
ENCRYPTION
DEFAULT STORAGE(ENCRYPT);
```

## PostgreSQL

Amazon provides the ability to encrypt data at rest (data in persistent storage). When enabled, it automatically encrypts the database server storage, automated backups, read replicas, and snapshots using the **AES-256** algorithm via **AWS KMS**. Encryption/decryption is transparent — no performance impact, no user intervention, and no client modifications required.

### Enable encryption
As part of the database settings you are asked to enable encryption and choose a root key. You can choose the default account key or define a specific key by IAM AWS KMS ARN (from your account or a different account).

### Create an encryption key
1. In the AWS KMS console, choose **Customer managed keys** and create a new key.
2. Choose relevant options, then **Next**.
3. Enter an **Alias** (the key name), then **Next**.
4. Skip **Define Key Administrative Permissions**, then **Next**.
5. Assign the key to the users who interact with Aurora.
6. The final step shows the key ARN and its account.
7. Choose **Finish**; the key appears under customer managed keys.

Then set the root encryption key using the ARN (or pick from the list) and finish the instance launch.

### SSE-S3 encryption overview
Server-side encryption with Amazon S3-managed keys (**SSE-S3**) uses multi-factor encryption: S3 encrypts each object with a unique key and encrypts that key with a periodically rotated root key. SSE-S3 uses **AES-256**. Once a bucket is enabled with SSE, any API call must include the `x-amz-server-side-encryption` header, and the AWS CLI must add the `--sse` switch.

**Enable SSE-S3 (via AWS Glue):**
1. Sign in to the AWS Glue console.
2. Create an AWS Glue job.
3. Define the role, bucket, and script to use.
4. Enable Server-Side Encryption.
5. Submit and run the job.

After this, files are accessible only via AWS CLI S3 with `--sse`, or by adding `x-amz-server-side-encryption` to API calls.

## Conversion notes
- No direct equivalent to Oracle TDE; Aurora PostgreSQL uses **Amazon RDS/Aurora storage-level encryption** backed by **AWS KMS (AES-256)**, configured at instance creation rather than in SQL.
- Aurora encryption is **all-or-nothing at the storage level** — there is no per-column or per-tablespace encryption equivalent like Oracle's `ENCRYPT` column clause.
- Encryption must typically be chosen **when the cluster is created**; plan for it before provisioning.
- Aurora encryption transparently covers storage, automated backups, read replicas, and snapshots — eliminating the manual keystore/wallet management Oracle requires.
- Like Oracle TDE, Aurora storage encryption protects **data at rest only**; use TLS/SSL for data in transit.
- For application-level or fine-grained encryption needs that TDE column encryption covered, consider the PostgreSQL `pgcrypto` extension or handle encryption in the application layer.
- SSE-S3 is relevant for data staged in S3 (e.g., DMS/Glue pipelines), not for the database storage itself.
