# Security — Oracle → Aurora MySQL Reference Index

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> Section: Security

Reference material distilled from the AWS Oracle to Aurora MySQL Migration Playbook (Security chapter). Each file follows a common structure: topic title, source/URL, conversion category, SCT automation, Oracle usage (with example), MySQL usage (with example), and conversion notes.

| Topic | File | Conversion category | SCT automation |
|---|---|---|---|
| Encrypted connections | [encrypted-connections.md](encrypted-connections.md) | Manual | N/A |
| Oracle TDE & Aurora MySQL encryption / column encryption | [tde-and-encryption.md](tde-and-encryption.md) | Manual | N/A |
| Oracle roles & MySQL privileges | [roles-and-privileges.md](roles-and-privileges.md) | Assisted | N/A |
| Oracle database users & MySQL users | [users.md](users.md) | Assisted | N/A |

## Key takeaways

- **Encrypted connections** — Oracle native Net Services encryption (`sqlnet.ora`) vs. MySQL TLS; configure TLS per user/client on RDS/Aurora.
- **Encryption at rest** — Oracle TDE (wallet/keystore, tablespace/column) maps to managed AWS KMS AES-256 encryption (enabled only at instance creation); column-level encryption maps to MySQL `AES_ENCRYPT`/`AES_DECRYPT` functions.
- **Roles vs. privileges** — MySQL 5.7 has no roles (grant privileges directly); MySQL 8 / RDS MySQL 8 reintroduces roles.
- **Users** — Similar lifecycle but key model differences: Oracle user == schema; MySQL users are host-qualified and separate from databases. Oracle OS/external auth maps to MySQL IAM database authentication.
