# Security — SQL Server → Aurora PostgreSQL Reference Index

Distilled reference material from the AWS *SQL Server → Aurora PostgreSQL Migration Playbook*, security section. Each file follows a common structure: source/URL, conversion category, SQL Server usage (with examples), PostgreSQL usage (with examples), and conversion notes.

| Topic | File | Conversion category | Key difference |
|---|---|---|---|
| Data Control Language (GRANT / REVOKE) | [data-control-language.md](data-control-language.md) | Automatic (5★) | Similar syntax; PostgreSQL has no `DENY` |
| Transparent Data Encryption (TDE) | [tde.md](tde.md) | Assisted (4★) | Storage-level encryption managed by Amazon RDS + KMS |
| Column Encryption | [column-encryption.md](column-encryption.md) | Assisted (3★) | `pgcrypto` functions vs SQL Server key hierarchy |
| Users and Roles | [users-and-roles.md](users-and-roles.md) | Assisted (3★) | No users in PostgreSQL — roles only; no Windows Auth |

## Summary

- **DCL** is the most portable: `GRANT`/`REVOKE` map directly. The main gap is SQL Server's `DENY`, which has no PostgreSQL equivalent and must be re-modeled.
- **TDE** changes implementation model entirely — from in-database SQL DDL to RDS storage-level encryption configured via KMS at instance creation.
- **Column encryption** is functionally similar but requires the `pgcrypto` extension and uses `pgp_sym_encrypt`/`pgp_sym_decrypt` instead of SQL Server's `EncryptByKey`/certificate hierarchy.
- **Users and roles** collapse SQL Server's two-tier login/user model into PostgreSQL's single cluster-wide role concept; Windows Authentication has no equivalent.
