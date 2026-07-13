# Security — SQL Server → Aurora MySQL

> Source: AWS SQL Server→Aurora MySQL Migration Playbook
> Chapter: https://docs.aws.amazon.com/dms/latest/sql-server-to-aurora-mysql-migration-playbook/chap-sql-server-aurora-mysql.security.html

Reference files distilled from the **Migrating security features to Aurora MySQL** chapter, covering user permissions, access control, data encryption, and secure connections.

| Topic | File | Conversion category | SCT automation |
|---|---|---|---|
| Column Encryption | [column-encryption.md](column-encryption.md) | Manual | N/A |
| Data Control Language (DCL) | [data-control-language.md](data-control-language.md) | Assisted | N/A |
| Transparent Data Encryption (TDE) | [transparent-data-encryption.md](transparent-data-encryption.md) | Manual | N/A |
| Users and Roles | [users-roles.md](users-roles.md) | Manual | N/A |
| Encrypted Connections | [encrypted-connections.md](encrypted-connections.md) | Manual | N/A |

## Key themes

- **Encryption at rest**: SQL Server per-database TDE → Aurora/RDS storage-level encryption via AWS KMS, configured at instance creation only.
- **Column-level encryption**: SQL Server's key/certificate hierarchy → simpler MySQL `AES_ENCRYPT`/`AES_DECRYPT` with client-hashed keys; no asymmetric support.
- **Permissions (DCL)**: `GRANT`/`REVOKE` map closely; MySQL has **no `DENY`** and revokes only at the granularity granted.
- **Users & roles**: SQL Server Logins+Users+Roles → single MySQL Users (host-qualified); no native roles in base engine — use AWS IAM authentication / RDS for MySQL 8 roles.
- **Encrypted connections**: both use TLS; configure client to trust the Aurora/RDS CA bundle.
