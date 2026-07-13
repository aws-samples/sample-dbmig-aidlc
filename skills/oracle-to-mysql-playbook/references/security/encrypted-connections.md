# Encrypted Connections

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.security.encryptedconnections.html

**Conversion category:** Manual
**SCT automation:** N/A

With AWS DMS, you can secure data transmission between the replication instance and the source or target database by using encrypted connections, providing a private encrypted tunnel for data transfer.

## Oracle

Oracle Database supports encrypting incoming data out of the box using native Oracle Net Services. Data sent to and from the server can be encoded using:

- AES (Advanced Encryption Standard)
- ARIA (Academia, Research Institute, and Agency)
- GOST (GOsudarstvennyy STandart)
- SEED (Korea Information Security Agency)
- Triple-DES (3DES)

Algorithms are specified in the `sqlnet.ora` file for clients and servers. Example directives:

```
# sqlnet.ora
SQLNET.ENCRYPTION_SERVER = REQUIRED
SQLNET.ENCRYPTION_TYPES_SERVER = (AES256, AES192, AES128)
SQLNET.CRYPTO_CHECKSUM_SERVER = REQUIRED
SQLNET.CRYPTO_CHECKSUM_TYPES_SERVER = (SHA256)
```

SSL/TLS connections to the Oracle database are supported starting with Oracle 12c in the standard edition.

## MySQL

MySQL supports encrypted connections between clients and the server using the TLS (Transport Layer Security) protocol. TLS is sometimes referred to as SSL, but MySQL does not actually use the SSL protocol because its encryption is weak.

OpenSSL 1.1.1 supports the TLS v1.3 protocol for encrypted connections. Amazon RDS for MySQL version 8.0.16 and higher supports TLS v1.3 if both the server and client are compiled with OpenSSL 1.1.1 or higher.

```sql
-- Require an encrypted connection for a user account
ALTER USER 'testuser'@'%' REQUIRE SSL;

-- Inspect the negotiated TLS version / cipher for the session
SHOW STATUS LIKE 'Ssl_version';
SHOW STATUS LIKE 'Ssl_cipher';
```

```bash
# Client connecting with TLS
mysql --ssl-mode=REQUIRED -h myhost -u testuser -p
```

## Conversion notes

- Both engines support transport encryption; this is an environmental/configuration concern, not a schema object, so conversion is manual.
- Oracle native Net Services encryption (AES/ARIA/GOST/SEED/3DES via `sqlnet.ora`) has no direct MySQL equivalent — MySQL relies on TLS for in-transit encryption.
- Configure TLS at the connection layer in MySQL (`REQUIRE SSL` per user, `--ssl-mode` on the client) rather than via an Oracle-style network parameter file.
- On Amazon RDS/Aurora MySQL, prefer TLS v1.2/v1.3; v1.3 needs server and client built on OpenSSL 1.1.1+ (RDS MySQL 8.0.16+).
