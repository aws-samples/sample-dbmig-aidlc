# Oracle Database Users and MySQL Users

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.security.users.html

**Conversion category:** Assisted
**SCT automation:** N/A

Key difference: syntax and option differences, similar functionality.

## Oracle

Database user accounts authenticate connecting sessions and authorize access to database objects. Providing application access generally means: (1) create a user account (usually password-authenticated), (2) assign permissions to objects and system privileges, (3) applications connect with the username/password.

Common user properties: granting privileges/roles, default tablespace, tablespace quotas, password policy/complexity, account lock/unlock.

Authentication mechanisms:
- **Username + password** — default.
- **External** — OS or third-party software such as Kerberos.
- **Global** — enterprise directory service such as Active Directory or Oracle Internet Directory.

**Oracle schemas vs. users:** in Oracle a user equals a schema. Creating a user with `CREATE USER` also creates an identically named schema to hold that account's objects. You cannot create schemas and users separately; new schemas start empty.

**Oracle 12c user types:**
- **Common users** — created in all containers (root + PDBs); must use the `C##` prefix.
- **Local users** — created only in a specific PDB; identical usernames may exist across different PDBs.

```sql
-- Create a common user, grant privileges/roles, set profile, unlock, expire password
CREATE USER c##test_user IDENTIFIED BY password DEFAULT TABLESPACE USERS;
GRANT CREATE SESSION TO c##test_user;
GRANT RESOURCE TO c##test_user;
ALTER USER c##test_user ACCOUNT UNLOCK;
ALTER USER c##test_user PASSWORD EXPIRE;
ALTER USER c##test_user PROFILE ORA_STIG_PROFILE;

-- Create a local user inside a PDB
ALTER SESSION SET CONTAINER = my_pdb1;
CREATE USER app_user1 IDENTIFIED BY password DEFAULT TABLESPACE USERS;
```

## MySQL

User accounts authenticate sessions and authorize object access. `CREATE USER` creates a row in the `mysql.user` system table; unspecified properties take defaults:
- **Authentication** — plugin from `default_authentication_plugin`, empty credentials.
- **SSL/TLS** — None.
- **Resource limits** — Unlimited.
- **Password management** — `PASSWORD EXPIRE DEFAULT`.
- **Account locking** — `ACCOUNT UNLOCK`.

New accounts have no privileges; use `GRANT` to assign them.

Common user properties: granting privileges, password policy/complexity, account lock/unlock, authentication method, host-based user naming (which hosts the user may log in from), and profiling such as `MAX_QUERIES_PER_HOUR` or `MAX_USER_CONNECTIONS`.

Authentication mechanisms:
- **Username + password** — default.
- **External** — OS or third-party software, such as an IAM user.
- **Global** — enterprise directory service such as Active Directory.

**IAM authentication** (equivalent to Oracle OS authentication): on RDS for MySQL or Aurora MySQL, authenticate using an IAM-issued authentication token instead of a password. Benefits: SSL-encrypted traffic, centralized IAM access management, and EC2 instance-profile credentials for apps. Limited to a maximum of 20 new connections per second.

```sql
-- Create user with password expiry, grant privileges, set profiling limits
CREATE USER 'testuser'
    IDENTIFIED BY 'new_password' PASSWORD EXPIRE;
GRANT ALL ON test_db.* TO 'testuser';
GRANT CREATE USER ON *.* TO 'testuser';
ALTER USER 'testuser' WITH MAX_QUERIES_PER_HOUR 90;

-- IAM-authenticated user (IAM user/role must exist with the same name)
CREATE USER jane_doe IDENTIFIED WITH AWSAuthenticationPlugin AS 'RDS';
```

## Conversion notes

- Core lifecycle (create user, grant, expire password, lock/unlock) maps closely; mostly syntactic differences, hence assisted.
- Biggest model difference: in Oracle a user **is** a schema, so objects live in the user's namespace. In MySQL a "schema" is a database and users are separate from databases — recreate Oracle schema objects in target MySQL databases and grant the corresponding users access (`GRANT ... ON db.*`).
- MySQL accounts are host-qualified (`'user'@'host'`); decide the allowed host pattern (e.g. `'%'`) — Oracle has no host component in the username.
- Oracle 12c common (`C##`) / local PDB users have no MySQL equivalent; flatten to ordinary MySQL users.
- Map Oracle external/OS authentication and Kerberos to MySQL IAM database authentication (`IDENTIFIED WITH AWSAuthenticationPlugin AS 'RDS'`) on RDS/Aurora — note the 20 new-connections-per-second limit.
- Translate Oracle profiles/resource limits to MySQL account resource options (`MAX_QUERIES_PER_HOUR`, `MAX_USER_CONNECTIONS`, etc.). Oracle tablespace/quota properties have no MySQL counterpart.
