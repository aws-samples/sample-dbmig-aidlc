# Oracle Database Users and PostgreSQL Users

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.security.users.html

**Conversion category:** Assisted (Three star feature compatibility)
**SCT automation:** N/A

## Oracle

Database user accounts authenticate connecting sessions and authorize access for individual users to specific database objects. DBAs grant privileges to user accounts, and applications use user accounts to access database objects.

### Steps for providing database access to applications
1. Create a user account in the database (typically password-authenticated; other methods exist).
2. Assign permissions to the user enabling access to certain database objects and system permissions.
3. Connecting applications authenticate using the database username and password.

### Common user properties
- Granting privileges or roles (collections of privileges) to the user.
- Defining the user's default database tablespace.
- Assigning tablespace quotas.
- Configuring password policy/complexity, and locking/unlocking the account.

### Authentication mechanisms
- **Username and Password** — used by default.
- **External** — using the OS or third-party software (such as Kerberos).
- **Global** — enterprise directory service (such as Active Directory or Oracle Internet Directory).

### Oracle schemas compared to users
In Oracle, **a user equals a schema**. A user is the account you connect with; a schema is the set of objects (tables, views, etc.) belonging to that account.
- You cannot create schemas and users separately — creating a user also creates a same-named schema.
- `CREATE USER` creates both a login user and a schema for storing objects.
- Newly created schemas are empty but objects (e.g., tables) can be created within them.

### Database users in Oracle 12c
- **Common Users** — created in all containers (root and PDBs); must have the `C##` prefix.
- **Local Users** — created only in a specific PDB; identically named local users can exist across multiple PDBs.

**Examples**

Create a common user with a default tablespace; grant privileges/roles; assign a profile, unlock, and force password change; then create a local user in `my_pdb1`:

```sql
CREATE USER c##test_user IDENTIFIED BY password DEFAULT TABLESPACE USERS;
GRANT CREATE SESSION TO c##test_user;
GRANT RESOURCE TO c##test_user;
ALTER USER c##test_user ACCOUNT UNLOCK;
ALTER USER c##test_user PASSWORD EXPIRE;
ALTER USER c##test_user PROFILE ORA_STIG_PROFILE;
ALTER SESSION SET CONTAINER = my_pdb1;
CREATE USER app_user1 IDENTIFIED BY password DEFAULT TABLESPACE USERS;
```

## PostgreSQL

In PostgreSQL there are **no users, only roles**. A role with the connect (`LOGIN`) privilege can be considered a user.

See the Roles reference (`roles.md`) for the full set of `CREATE ROLE` / `CREATE USER` examples and the Oracle→PostgreSQL command mapping.

## Conversion notes
- PostgreSQL has **no separate "user" object** — convert Oracle users into roles created `WITH LOGIN` (or `CREATE USER`, which implies `LOGIN`).
- **User ≠ schema in PostgreSQL.** Oracle automatically creates a same-named schema with each user; in PostgreSQL you must create the schema separately with `CREATE SCHEMA`.
- **Common vs. local users:** Oracle common users (C## prefix) map to cluster-global login roles; Oracle local (per-PDB) users have **no equivalent** because PostgreSQL roles are always cluster-wide.
- **Authentication:** Oracle's external (Kerberos/OS) and global (directory service) authentication are not directly supported on Aurora PostgreSQL; plan to migrate to password auth (or IAM database authentication where applicable).
- **Profiles, password policy/complexity, and tablespace quotas** do not have direct PostgreSQL equivalents — handle via role attributes (`CONNECTION LIMIT`, `VALID UNTIL`, `NOLOGIN`) and external policy where needed.
- For lock/unlock semantics, use `ALTER ROLE ... NOLOGIN` / `LOGIN` instead of `ACCOUNT LOCK`/`UNLOCK`.
