# Oracle Instance Parameters and Aurora MySQL Parameter Groups

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.configuration.parameters.html

**Conversion category:** N/A (feature compatibility: one star)
**SCT automation:** N/A

> **Reviewed for Aurora MySQL 8.4 and 3** (validated on 8.4.8 and 3.13.0, 2026-10-29): Current families aurora-mysql8.4 / aurora-mysql8.0 (verified), CLI example with a stricter sql_mode, list of commonly changed parameters with verified defaults, 8.4 removed parameters.

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

**Create a new parameter group:** RDS console → **Databases** → **Parameter groups** → **Create parameter group** → set **Parameter group family** (`aurora-mysql8.4` for Aurora MySQL 8.4, `aurora-mysql8.0` for version 3) → choose **Type** (DB cluster parameter group or DB parameter group) → **Create**.

```bash
aws rds create-db-cluster-parameter-group --db-cluster-parameter-group-name app-aurora-mysql84 \
  --db-parameter-group-family aurora-mysql8.4 --description "app cluster params"
aws rds modify-db-cluster-parameter-group --db-cluster-parameter-group-name app-aurora-mysql84 \
  --parameters "ParameterName=sql_mode,ParameterValue='STRICT_TRANS_TABLES,ONLY_FULL_GROUP_BY,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION',ApplyMethod=immediate"
```

> Note: you cannot edit the default parameter group. Create a custom group to apply changes to the cluster and its instances.

**Modify an existing group:** RDS console → **Parameter groups** → select group → **Parameter group actions** → **Edit** → change values → **Save changes**.

## Conversion notes

- There is no Oracle-style `SPFILE`/`PFILE` on Aurora and no `ALTER SYSTEM`; all instance/cluster config flows through parameter groups in the RDS console (or CLI/API).
- Distinguish **cluster parameter groups** (apply to the whole Aurora cluster) from **DB parameter groups** (per instance) when mapping former `ALTER SYSTEM` settings.
- The default parameter group is read-only — always create a custom group.
- Match the **parameter group family** to the engine version: `aurora-mysql8.4` or `aurora-mysql8.0` (both used for this review's validation clusters). A group from one family cannot be attached to the other, so a 3 → 8.4 upgrade needs a new group.
- Parameters an Oracle migration usually changes (all defaults verified on 3.13 and 8.4.8): `sql_mode` (Aurora default is **empty** — no strict mode; corrected 2026-10-30), `transaction_isolation` (default `REPEATABLE-READ`; Oracle behaves like `READ-COMMITTED`), `time_zone` (default UTC), `group_concat_max_len` (1024), `log_bin_trust_function_creators` (0), `performance_schema` (0 on the default Serverless v2 group; static), `binlog_format` (off unless set; static), `lower_case_table_names` (0; can only be set at cluster creation).
- Aurora MySQL 8.4 removed `expire_logs_days`, `binlog_transaction_dependency_tracking` and `default_authentication_plugin` (replaced by `authentication_policy`) — verified.
- Some parameters are static (require an instance reboot to apply) vs dynamic, analogous to Oracle's `scope=spfile` vs `scope=memory`/`both` distinction.
