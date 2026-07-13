# Oracle Multitenant and MySQL Databases

> Source: AWS Oracle→Aurora MySQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-mysql-migration-playbook/chap-oracle-aurora-mysql.special.multitenant.html

**Conversion category:** Manual (three-star feature compatibility) — distribute load, applications, and users across multiple instances/databases.
**SCT automation:** N/A

## Oracle

Oracle 12c introduced multitenant architecture: a container database (CDB) hosting one or more pluggable databases (PDB), a 1:N instance-to-database relationship (pre-12c was 1:1).

- **CDB** — created with the 12c install; holds control files, system tablespaces, instance undo (unless 12.2 local undo) and redo logs, and the data dictionary for the root and all PDBs. Contains a single root container (`CDB$ROOT`) and a single seed PDB template.
- **PDB** — an independent database (container) for application data; has its own data/system data files, tablespaces, temp files, and metadata (data dictionary). Created from `pdb$seed` or as a clone of an existing PDB.

Advantages: application isolation, portable schema collections, cloning/transport between CDBs, manage-many-as-one, per-PDB security/resources, consolidation, easier per-PDB patch/upgrade, CDB- and PDB-level backups. 18c adds DBCA PDB Clone, Refreshable PDB Switchover, CDB Fleet Management; 19c adds multiple PDBs per CDB in sharded environments.

List PDBs:

```sql
SHOW PDBS;
-- CON_ID  CON_NAME  OPEN MODE   RESTRICTED
-- 2       PDB$SEED  READ ONLY   NO
-- 3       PDB1      READ WRITE  NO
```

Create / open / clone PDBs:

```sql
CREATE PLUGGABLE DATABASE PDB2 admin USER ora_admin
IDENTIFIED BY ora_admin FILE_NAME_CONVERT=('/pdbseed/','/pdb2/');

ALTER PLUGGABLE DATABASE PDB2 OPEN READ WRITE;

CREATE PLUGGABLE DATABASE PDB3
  FROM PDB2 FILE_NAME_CONVERT= ('/pdb2/','/pdb3/');
```

## MySQL

Aurora MySQL offers a simpler model: create multiple databases under one Aurora cluster, and/or use separate clusters when full workload isolation is needed. Each cluster has one primary (read/write for all databases) and up to 15 read-only nodes for scale-out and HA.

Mapping: an Oracle **CDB/Instance** ≈ an Aurora **cluster**; an Oracle **PDB** ≈ a **database** inside the Aurora cluster (not all features comparable).

```sql
CREATE DATABASE db1;
CREATE DATABASE db2;
CREATE DATABASE db3;

SHOW DATABASES;
-- information_schema, mysql, performance_schema, db1, db2, db3, sys, tmp
```

Approximating 18c/19c PDB features in AWS:
- **PDB Clone** — not simple within an instance; use export/import for the same instance.
- **Refreshable PDB Switchover** — depends on granularity: same-instance failover via `CREATE DATABASE` + application failover; or two databases in different instances kept in sync via database links / AWS DMS with application failover.
- **CDB Fleet Management** — similar to AWS orchestration: manage multiple RDS instances (CDB) and their databases (PDB) centrally via console/CLI.

### Independent database backups

Oracle 12c can do logical (DataPump) and physical (RMAN) backups at CDB and PDB levels. Aurora MySQL: logical backups per-database with `mysqldump`; physical snapshots cover the **entire cluster** (single-database snapshot not supported). Snapshots are fast (storage-layer), but restoring a single database requires extra steps: restore the snapshot, export that database, and import it back into the original cluster.

## Conversion notes

- Map each PDB to a MySQL database inside an Aurora cluster (consolidation) or to a separate Aurora cluster (full isolation).
- Per-PDB physical backup/restore is not available — plan logical (`mysqldump`) backups for single-database granularity.
- PDB cloning/transport and refreshable switchover require AWS-native workarounds (export/import, DMS, replication, application failover).
- Centralized fleet management maps to RDS/Aurora console and CLI orchestration.
