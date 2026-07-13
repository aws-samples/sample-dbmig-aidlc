# Security References — Oracle → Aurora PostgreSQL

Distilled reference pages from the AWS Oracle→Aurora PostgreSQL Migration Playbook (Security chapter).

| File | Summary |
|---|---|
| [tde-and-encryption.md](./tde-and-encryption.md) | Oracle Transparent Data Encryption (TDE) column/tablespace encryption vs. Amazon Aurora storage-level encryption via AWS KMS (AES-256), plus SSE-S3 overview. Conversion category: Manual. |
| [roles.md](./roles.md) | Oracle roles (common/local, 12c) vs. PostgreSQL cluster-global roles, with full Oracle→PostgreSQL command mapping table. Conversion category: Assisted. |
| [users.md](./users.md) | Oracle database users (common/local, user=schema, auth mechanisms) vs. PostgreSQL — no users, only login roles; schemas created separately. Conversion category: Assisted. |
