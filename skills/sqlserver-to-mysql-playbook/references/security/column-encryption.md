# Column Encryption

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.security.columnencryption.html

**Conversion category:** Manual
**SCT automation:** N/A (No automation; three-star feature compatibility)

## SQL Server

SQL Server provides encryption/decryption functions to secure individual column contents. These functions can be used anywhere in code (not just on table columns) — e.g. encrypting application user security tokens passed as parameters. They follow the SQL Server encryption hierarchy and use the Windows Server Data Protection API. Symmetric encryption/decryption consumes minimal resources and works for large data sets.

Common functions:
- `EncryptByKey` / `DecryptByKey`
- `EncryptByCert` / `DecryptByCert`
- `EncryptByPassPhrase` / `DecryptByPassPhrase`
- `EncryptByAsymKey` / `DecryptByAsymKey`

(This does not cover TDE or AlwaysEncrypted end-to-end encryption.)

Syntax:

```sql
EncryptByKey ( <key GUID> , { 'text to be encrypted' }, { <use authenticator flag>}, { <authenticator> } );
DecryptByKey ( 'Encrypted Text' , <use authenticator flag>, { <authenticator> )
```

Example — encrypt an employee SSN:

```sql
-- Create a database master key
USE MyDatabase;
CREATE MASTER KEY
ENCRYPTION BY PASSWORD = '<REPLACE_WITH_STRONG_PASSWORD>';

-- Create a certificate and a symmetric key
CREATE CERTIFICATE Cert01
WITH SUBJECT = 'SSN';

CREATE SYMMETRIC KEY SSN_Key
WITH ALGORITHM = AES_256
ENCRYPTION BY CERTIFICATE Cert01;

-- Create the employees table
CREATE TABLE Employees
(
    EmployeeID INT PRIMARY KEY,
    SSN_encrypted VARBINARY(128) NOT NULL
);

-- Open the symmetric key for encryption
OPEN SYMMETRIC KEY SSN_Key
DECRYPTION BY CERTIFICATE Cert01;

-- Insert the encrypted data
INSERT INTO Employees (EmployeeID, SSN_encrypted)
VALUES
(1, EncryptByKey(Key_GUID('SSN_Key') , '1112223333', 1, HashBytes('SHA1', CONVERT(VARBINARY, 1)));

SELECT EmployeeID,
CONVERT(CHAR(10), DecryptByKey(SSN, 1 , HashBytes('SHA1', CONVERT(VARBINARY, EmployeeID)))) AS SSN
FROM Employees;

-- EmployeeID  SSN_Encrypted              SSN
-- 1           0x00F983FF436E32418132...  1112223333
```

## MySQL

Aurora MySQL provides encryption/decryption functions similar to SQL Server but with a much simpler security hierarchy that is easier to manage. The functions require the actual key as a string, so take extra measures to protect the data (e.g. hashing key values on the client).

Aurora MySQL supports AES and DES algorithms:
- `AES_ENCRYPT` / `AES_DECRYPT`
- `DES_ENCRYPT` / `DES_DECRYPT`

Notes:
- `ENCRYPT`, `DECRYPT`, `ENCODE`, `DECODE` are deprecated (MySQL 5.7.2 / 5.7.6). Asymmetric encryption is **not** supported in Aurora MySQL.
- Amazon RDS for MySQL 8 supports FIPS mode if compiled with OpenSSL and a FIPS Object Module is available at runtime.

Syntax:

```sql
[A|D]ES_ENCRYPT(<string to be encrypted>, <key string> [,<initialization vector>])
[A|D]ES_DECRYPT(<encrypted string>, <key string> [,<initialization vector>])
```

Recommendations:
- Use the optional initialization vector to circumvent whole-value replacement attacks. When encrypting column data, it is common to use an immutable key as the IV so decryption fails if a whole value moves to another row.
- Prefer SHA2 over SHA1/MD5 (known exploits exist for SHA1 and MD5).
- Sensitive data passed to these functions from the client is not encrypted unless using an SSL connection. AWS IAM database connections are encrypted with SSL by default.

Example — encrypt an employee SSN:

```sql
-- Create the employees table
CREATE TABLE Employees
(
    EmployeeID INT NOT NULL PRIMARY KEY,
    SSN_Encrypted BINARY(32) NOT NULL
);

-- Insert the encrypted data (UNHEX for more efficient storage and comparisons)
INSERT INTO Employees (EmployeeID, SSN_Encrypted)
VALUES (1, AES_ENCRYPT('1112223333', UNHEX(SHA2('REPLACE_WITH_STRONG_PASSWORD',512)), 1));

-- Verify decryption
SELECT EmployeeID,
SSN_Encrypted,
AES_DECRYPT(SSN_Encrypted, UNHEX(SHA2('REPLACE_WITH_STRONG_PASSWORD',512)), EmployeeID) AS SSN
FROM Employees;
```

## Conversion notes
- No SCT automation; conversion is manual.
- Aurora MySQL has a simpler, easier-to-manage hierarchy — no master keys, certificates, or symmetric-key objects. Keys are supplied directly to the functions as strings.
- Map SQL Server `EncryptByKey`/`DecryptByKey` (with certificate + symmetric key setup) to MySQL `AES_ENCRYPT`/`AES_DECRYPT` with a client-hashed key (e.g. `UNHEX(SHA2(...))`).
- Asymmetric encryption (`EncryptByAsymKey`, `EncryptByCert`) has no Aurora MySQL equivalent and must be redesigned.
- Use an initialization vector in MySQL to mitigate whole-value replacement attacks (SQL Server's authenticator flag serves a similar purpose).
- Ensure SSL/TLS connections to protect key/data in transit; IAM connections are SSL by default.
