# Oracle Instance Parameters and Aurora MySQL Parameter Groups

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.configuration.parameters.html

**Conversion category:** N/A (feature compatibility: one star)
**SCT automation:** N/A

**Key difference:** Use cluster and database (instance) parameter groups.

## Oracle

Oracle instance and database-level parameters are configured with `ALTER SYSTEM`. Some take effect dynamically; others require an instance restart. All parameters are stored in the binary **Server Parameter File (`SPFILE`)**, which can be exported to a text PFILE:

```sql
CREATE PFILE = 'my_init.ora' FROM SPFILE = 's_params.ora';
```

Persistence scope when modifying a parameter:

- `scope=spfile` — applies only after restart
- `scope=memory` — dynamic, not persistent across restart
- `scope=both` — dynamic and persistent

### Example

```sql
ALTER SYSTEM SET QUERY_REWRITE_ENABLED = TRUE SCOPE=BOTH;
```

## MySQL

Aurora MySQL restricts OS access, so parameters are changed through **Parameter Groups**, not files. Most MySQL parameters are configurable; some are disabled. Aurora is a cluster of instances, so parameters split into two classes:

| Parameter class | Controlled through | Example parameters |
|---|---|---|
| **Cluster-level** (one group per cluster) | Cluster parameter groups | `aurora_load_from_s3_role`, `default_password_lifetime`, `default_storage_engine` |
| **Database instance-level** (each instance can have its own group) | DB parameter groups | `autocommit`, `connect_timeout`, `innodb_change_buffer_max_size` |

### Examples

**Create a new parameter group:** RDS console → **Databases** → **Parameter groups** → **Create parameter group** → set **Parameter group family** (e.g. `aurora-mysql5.7`) → choose **Type** (DB parameter group) → **Create**.

> Note: you cannot edit the default parameter group. Create a custom group to apply changes to the cluster and its instances.

**Modify an existing group:** RDS console → **Parameter groups** → select group → **Parameter group actions** → **Edit** → change values → **Save changes**.

## Conversion notes

- There is no Oracle-style `SPFILE`/`PFILE` on Aurora and no `ALTER SYSTEM`; all instance/cluster config flows through parameter groups in the RDS console (or CLI/API).
- Distinguish **cluster parameter groups** (apply to the whole Aurora cluster) from **DB parameter groups** (per instance) when mapping former `ALTER SYSTEM` settings.
- The default parameter group is read-only — always create a custom group.
- Match the **parameter group family** to the engine version (e.g. `aurora-mysql5.7`).
- Some parameters are static (require an instance reboot to apply) vs dynamic, analogous to Oracle's `scope=spfile` vs `scope=memory`/`both` distinction.
