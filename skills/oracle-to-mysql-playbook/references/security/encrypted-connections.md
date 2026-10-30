# Encrypted Connections

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.security.encryptedconnections.html

**Conversion category:** Manual
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Verified TLS defaults: 8.4 enforces require_secure_transport=ON and only forward-secret GCM ciphers, 3.13 does not; CA bundle and verification, driver inventory, toolkit sslmode.

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

Verified on the validation clusters (default parameter groups):
| Setting | Aurora MySQL 3.13 | Aurora MySQL 8.4.8 |
|---|---|---|
| `require_secure_transport` | **OFF** | **ON** — unencrypted connections are refused |
| `tls_version` | `TLSv1.2,TLSv1.3` | `TLSv1.2,TLSv1.3` |
| `ssl_cipher` | includes CBC/SHA1 suites | forward-secret AES-GCM suites only (weak ciphers removed in 8.4) |
| Negotiated by the Data API | TLSv1.3 | TLSv1.3 |

- Set `require_secure_transport = ON` in the cluster parameter group on Aurora MySQL 3 too, rather than `REQUIRE SSL` per account.
- Clients must trust the RDS CA bundle (`global-bundle.pem`) and should verify the server (`--ssl-mode=VERIFY_IDENTITY`, PyMySQL `ssl={'ca': …}`). Plan for CA rotation; certificate rotation without restart is supported on both versions.
- Old drivers that only speak TLS 1.0/1.1 or legacy ciphers cannot connect to 8.4 at all — inventory them before migration.
- In this toolkit, set `sslmode: require` (or stricter) in `connections.yaml` for Aurora targets.
