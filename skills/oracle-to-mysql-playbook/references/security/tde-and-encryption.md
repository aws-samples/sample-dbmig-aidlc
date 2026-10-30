# Oracle Transparent Data Encryption and Aurora MySQL Encryption / Column Encryption

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.security.encryption.html

**Conversion category:** Manual
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): DES_ENCRYPT removed (verified), default aes-128-ecb ignores IVs (verified) — use aes-256-cbc with a random IV, AWS Encryption SDK alternative, default_table_encryption absent on Aurora, encrypt-via-snapshot-copy; fixed the example (BINARY(32) and IV 1 broke decryption; corrected version round-trips, verified); FIPS mode is ON (verified).

Both Oracle TDE and Aurora MySQL encryption provide data-at-rest protection. See [Encrypting Amazon RDS resources](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html).

## Oracle

Oracle uses Transparent Data Encryption (TDE) to encrypt data stored on media for data-at-rest protection at the OS level. Encryption is automatic and transparent to client applications; TDE does not address data in transit.

Characteristics:
- The `ADMINISTER KEY MANAGEMENT` system privilege is required to configure TDE.
- Data can be encrypted at the column level or the tablespace level.
- Key encryption is managed in an external TDE Master Encryption Module.
- There is one root key per database.

**Configure the root encryption key** (wallet location via `ENCRYPTION_WALLET_LOCATION`):

```
ENCRYPTION_WALLET_LOCATION=
    (SOURCE=
        (METHOD=FILE)
            (METHOD_DATA=
                (DIRECTORY=+ASM_file_path_of_the_diskgroup)))
```

**Create a password-based software keystore** (user needs `ADMINISTER KEY MANAGEMENT` or `SYSKM`):

```sql
sqlplus c##sec_admin as syskm
ADMINISTER KEY MANAGEMENT CREATE KEYSTORE '/etc/ORACLE/WALLETS/orcl' IDENTIFIED BY password;
```

**Open the keystore** (auto-login / local auto-login keystores open automatically):

```sql
ADMINISTER KEY MANAGEMENT SET KEYSTORE OPEN IDENTIFIED BY password;
```

**Set the software root (master) encryption key** (database must be `READ WRITE`):

```sql
ADMINISTER KEY MANAGEMENT SET KEY IDENTIFIED BY keystore_password WITH BACKUP USING 'emp_key_backup';
```

**Column encryption:**

```sql
CREATE TABLE employee (
    FIRST_NAME VARCHAR2(128),
    LAST_NAME VARCHAR2(128),
    EMP_ID NUMBER,
    SALARY NUMBER(6) ENCRYPT);

-- Choose algorithm / NO SALT
CREATE TABLE EMPLOYEE (
    FIRST_NAME VARCHAR2(128),
    LAST_NAME VARCHAR2(128),
    EMP_ID NUMBER ENCRYPT NO SALT,
    SALARY NUMBER(6) ENCRYPT USING '3DES168');

-- Change algorithm on existing table
ALTER TABLE EMPLOYEE REKEY USING 'SHA-1';

-- Remove column encryption
ALTER TABLE employee MODIFY (SALARY DECRYPT);
```

Supported column types: `BINARY_DOUBLE`, `BINARY_FLOAT`, `CHAR`, `DATE`, `INTERVAL DAY TO SECOND`, `INTERVAL YEAR TO MONTH`, `NCHAR`, `NUMBER`, `NVARCHAR2`, `RAW`, `TIMESTAMP` (incl. WITH TIME ZONE / WITH LOCAL TIME ZONE), `VARCHAR2`.

Column encryption can't be used with: non-B-tree indexes, range scan through an index, synchronous change data capture, transportable tablespaces, or foreign-key columns.

**Tablespace encryption** (`COMPATIBLE` >= 11.2.0.0):

```sql
CREATE TABLESPACE encrypt_ts
DATAFILE '$ORACLE_HOME/dbs/encrypt_df.dbf' SIZE 1M
ENCRYPTION USING 'AES256'
DEFAULT STORAGE (ENCRYPT);

CREATE TABLESPACE securespace_2
DATAFILE '/home/user/oradata/secure01.dbf' SIZE 150M
ENCRYPTION
DEFAULT STORAGE(ENCRYPT);
```

## MySQL

Amazon RDS/Aurora encrypts data at rest using AES-256 via AWS Key Management Service (AWS KMS). When enabled, it automatically encrypts DB storage, automated backups, read replicas, and snapshots — transparently, with no client changes and no performance impact.

**Encryption at rest** is enabled only at instance creation: choose a default account KMS key or a specific KMS ARN (own or cross-account).

**Create a KMS key (console):** Key Management Service → Customer managed keys → Create key → Symmetric / KMS key material → set alias → assign admin and usage permissions → Finish; then use the key's ARN as the master encryption key.

**FIPS mode:** `ssl_fips_mode` reports `ON` on Aurora MySQL 3.13 and 8.4.8 (verified); there is nothing to compile or enable. *(Corrected: the playbook described community RDS for MySQL FIPS build requirements.)*

**Table/schema encryption defaults (community MySQL 8 / RDS for MySQL — not Aurora):**
- `default_table_encryption` sets the default for newly created schemas and general tablespaces.
- `DEFAULT ENCRYPTION` clause sets a schema's encryption default; tables inherit the schema/tablespace default.
- `table_encryption_privilege_check` enforces defaults; `TABLE_ENCRYPTION_ADMIN` privilege permits overriding them.

**SSE-S3:** Server-side encryption with S3-managed keys uses AES-256. After enabling on a bucket, include the `x-amz-server-side-encryption` header in API calls (or use `aws s3 --sse`).

**Column encryption functions** (require the key as a string — protect it, e.g. hash on the client): `AES_ENCRYPT`, `AES_DECRYPT`. **`DES_ENCRYPT`/`DES_DECRYPT` were removed in MySQL 8.0** (error 1305 on 3.13 and 8.4, verified). The default `block_encryption_mode` is `aes-128-ecb` (verified), which ignores the IV — set `SET SESSION block_encryption_mode = 'aes-256-cbc'` (or in the parameter group) and pass a random IV (`RANDOM_BYTES(16)`) stored with the ciphertext.

```sql
-- Syntax (AES only; DES_* no longer exist)
AES_ENCRYPT(<string to encrypt>, <key string> [, <initialization vector>])
AES_DECRYPT(<encrypted string>, <key string> [, <initialization vector>])
```

*(Corrected example: the playbook stored ciphertext in `BINARY(32)`, which zero-pads the
16-byte ciphertext so `AES_DECRYPT` returns NULL, and passed IV `1`, which CBC mode rejects.
The version below round-trips on 3.13 and 8.4.8, verified.)*

```sql
CREATE TABLE Employees (
    EmployeeID    INT NOT NULL PRIMARY KEY,
    SSN_IV        BINARY(16) NOT NULL,
    SSN_Encrypted VARBINARY(64) NOT NULL);

SET SESSION block_encryption_mode = 'aes-256-cbc';
SET @iv = RANDOM_BYTES(16);
INSERT INTO Employees (EmployeeID, SSN_IV, SSN_Encrypted)
VALUES (1, @iv, AES_ENCRYPT('1112223333', UNHEX(SHA2('REPLACE_WITH_STRONG_PASSWORD',512)), @iv));

SELECT EmployeeID,
    CAST(AES_DECRYPT(SSN_Encrypted, UNHEX(SHA2('REPLACE_WITH_STRONG_PASSWORD',512)), SSN_IV) AS CHAR) AS SSN
FROM Employees;
```

## Conversion notes

- Oracle TDE (tablespace/column, wallet/keystore, master key) maps to Aurora/RDS at-rest encryption via AWS KMS — fully managed, transparent, AES-256. There is no Oracle-style keystore/wallet to migrate; encryption is an instance-creation setting.
- Aurora MySQL at-rest encryption can only be enabled at instance creation time — plan this before migration; you cannot toggle it on an existing instance.
- Oracle column-level `ENCRYPT`/`DECRYPT` DDL has no direct equivalent. For application-level column encryption, use MySQL `AES_ENCRYPT`/`AES_DECRYPT` and store ciphertext in a `VARBINARY` column (round trip verified on both versions). Better: encrypt in the application with the AWS Encryption SDK and KMS so the key never reaches the database or its logs.
- `default_table_encryption` and `table_encryption_privilege_check` **do not exist on Aurora MySQL** (error 1193 on 3.13 and 8.4, verified), so the "Table/schema encryption defaults" above apply to community MySQL / RDS for MySQL only. Aurora encrypts the whole cluster volume with KMS; drop `ENCRYPTION='Y'` table options from converted DDL.
- An unencrypted Aurora cluster cannot be encrypted in place; restore an encrypted copy from a snapshot (copy the snapshot with a KMS key).
- Use a random 16-byte IV per value (`RANDOM_BYTES(16)`) stored next to the ciphertext, with a CBC/CFB/OFB `block_encryption_mode`; a PK or constant is not a valid IV. Prefer SHA2 over SHA1/MD5 for deriving keys.
- Keys passed to MySQL encryption functions travel in plaintext unless the connection uses SSL/TLS; IAM database authentication encrypts connections with SSL by default.
