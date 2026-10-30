# Encrypted Connections

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.security.encryptedconnections.html

**Conversion category:** Manual (configuration, not code)
**SCT automation:** N/A (No automation; three-star feature compatibility)

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Verified TLS defaults: 8.4 enforces require_secure_transport and GCM-only ciphers, 3.13 does not; Force Encryption and TrustServerCertificate mappings.

## SQL Server

SQL Server can encrypt data across communication channels. Encrypted connections are enabled for a SQL Server Database Engine instance and use SQL Server Configuration Manager to specify a certificate.

- The server must have a certificate provisioned (import it into Windows).
- The client machine must be set up to trust the certificate's root authority.

> Starting with SQL Server 2016 (13.x), SSL has been discontinued — use TLS instead.

## MySQL

MySQL supports encrypted client/server connections using the **TLS** (Transport Layer Security) protocol. TLS is sometimes called SSL, but MySQL doesn't actually use the SSL protocol because its encryption is weak.

- OpenSSL 1.1.1 supports the TLS v1.3 protocol for encrypted connections.
- Amazon RDS for MySQL 8.0.16 and higher supports TLS v1.3 if both server and client are compiled with OpenSSL 1.1.1 or higher.

## Conversion notes
- Both engines secure connections with TLS; concepts map closely. No SQL-level conversion — this is a connection/instance configuration concern.
- SQL Server uses SQL Server Configuration Manager + a Windows-provisioned certificate with a trusted root on the client. Aurora MySQL/RDS provides server certificates; configure the client (driver/connection string) to use TLS and trust the RDS/Aurora CA bundle.
- Use TLS (not legacy SSL). Prefer TLS v1.3 where supported (RDS for MySQL 8.0.16+ with OpenSSL 1.1.1+).
- IAM database authentication encrypts connections with SSL/TLS by default.

Verified defaults (default parameter groups):
| Setting | Aurora MySQL 3.13 | Aurora MySQL 8.4.8 |
|---|---|---|
| `require_secure_transport` | OFF | **ON** — plaintext connections refused |
| `tls_version` | `TLSv1.2,TLSv1.3` | `TLSv1.2,TLSv1.3` |
| Ciphers | includes CBC/SHA1 suites | forward-secret AES-GCM only |

- Set `require_secure_transport = ON` on Aurora MySQL 3 too (≈ SQL Server *Force Encryption*).
- Clients must trust the RDS CA bundle (`global-bundle.pem`) and should verify the server name (≈ `TrustServerCertificate=False`). Old drivers that only speak TLS 1.0/1.1 cannot connect to 8.4.
- Toolkit: set `sslmode: require` (or stricter) in `connections.yaml`.
