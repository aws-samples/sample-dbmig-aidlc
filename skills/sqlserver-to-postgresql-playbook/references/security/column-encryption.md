# Column Encryption

> Source: AWS SQL Server→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-postgresql-migration-playbook/chap-sql-server-aurora-pg.security.columnencryption.html

**Conversion category:** Assisted (three-star compatibility — syntax and option differences, similar functionality)
**SCT automation:** N/A

## SQL Server

SQL Server provides functions to encrypt/decrypt individual columns. They are not limited to table columns — a common use case is encrypting application security tokens passed as parameters. Common functions:

- `EncryptByKey` / `DecryptByKey`
- `EncryptByCert` / `DecryptByCert`
- `EncryptByPassPhrase` / `DecryptByPassPhrase`
- `EncryptByAsymKey` / `DecryptByAsymKey`

These follow the SQL Server encryption hierarchy, which uses the Windows Server Data Protection API. Symmetric encryption consumes minimal resources and is suitable for large data sets. (This is separate from TDE and Always Encrypted.)

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

-- Create the table
CREATE TABLE Employees
(
  EmployeeID INT PRIMARY KEY,
  SSN_encrypted VARBINARY(128) NOT NULL
);

-- Open the symmetric key for encryption
OPEN SYMMETRIC KEY SSN_Key
DECRYPTION BY CERTIFICATE Cert01;

-- Insert encrypted data
INSERT INTO Employees (EmployeeID, SSN_encrypted)
VALUES
(1, EncryptByKey(Key_GUID('SSN_Key') , '1112223333', 1, HashBytes('SHA1', CONVERT(VARBINARY, 1)));

-- Decrypt on read
SELECT EmployeeID,
CONVERT(CHAR(10), DecryptByKey(SSN, 1 , HashBytes('SHA1', CONVERT(VARBINARY, EmployeeID)))) AS SSN
FROM Employees;
```

## PostgreSQL

Aurora PostgreSQL provides similar encryption/decryption functions via the `pgcrypto` extension, which must be installed first:

```sql
CREATE EXTENSION pgcrypto;
```

Supported algorithms: MD5, SHA1, SHA224/256/384/512, Blowfish, AES, raw encryption, PGP symmetric encryption, PGP public-key encryption.

Syntax (`PGP_SYM_ENCRYPT` / `PGP_SYM_DECRYPT`):

```sql
pgp_sym_encrypt(data text, psw text [, options text ]) returns bytea
pgp_sym_decrypt(msg bytea, psw text [, options text ]) returns text
```

Example — encrypt an employee SSN:

```sql
-- Create the table
CREATE TABLE users (id SERIAL, name VARCHAR(60), pass TEXT);

-- Insert encrypted data
INSERT INTO users (name, pass) VALUES ('John', PGP_SYM_ENCRYPT('123456', 'AES_KEY'));

-- Verify data is encrypted
SELECT * FROM users;
-- id  name  pass
-- 2   John  \xc30d04070302c30d07ff8b3b12f26ad233015a72bab4d3bb73f5a80d5187b1b...

-- Decrypt with the encryption key
SELECT name, PGP_SYM_DECRYPT(pass::bytea, 'AES_KEY') as pass
FROM users WHERE (name LIKE '%John%');
-- name  pass
-- John  123456

-- Update encrypted data
UPDATE users SET (name, pass) = ('John', PGP_SYM_ENCRYPT('0000', 'AES_KEY')) WHERE id='2';
```

## Conversion notes

- Both engines support column-level encryption with similar functionality but different syntax and options.
- SQL Server uses a key/certificate hierarchy (master key → certificate → symmetric key) and requires explicitly opening the symmetric key before use. PostgreSQL passes the password/key directly to the function call (no separate OPEN step).
- Install the `pgcrypto` extension before using PostgreSQL encryption functions.
- Map SQL Server `EncryptByKey`/`DecryptByKey` (and passphrase variants) to PostgreSQL `pgp_sym_encrypt`/`pgp_sym_decrypt` (symmetric) or PGP public-key functions as appropriate.
- Encrypted columns are stored as `VARBINARY` in SQL Server vs `bytea`/`TEXT` in PostgreSQL; cast to `bytea` when decrypting.
- This covers column-level encryption only — not TDE or Always Encrypted end-to-end encryption.
- See the PostgreSQL `pgcrypto` documentation for the full set of available functions and algorithms.
