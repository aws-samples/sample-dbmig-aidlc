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
- **Roles vs. privileges** — Aurora MySQL 3 / 8.4 support roles; set default roles (`SET DEFAULT ROLE ALL`), because `activate_all_roles_on_login` is OFF.
- **Users** — Similar lifecycle but key model differences: Oracle user == schema; MySQL users are host-qualified and separate from databases. Oracle OS/external auth maps to MySQL IAM database authentication.

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): 8.4 enforces TLS (`require_secure_transport` ON) and `caching_sha2_password`; roles native; `DES_ENCRYPT` removed; `AWSAuthenticationPlugin` for IAM.
