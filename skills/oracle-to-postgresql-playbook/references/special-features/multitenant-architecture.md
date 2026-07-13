# Multitenant Architecture

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.special.multitenant.html

**Conversion category:** Assisted (Three-star feature compatibility)
**SCT automation:** N/A

## Oracle

Oracle 12c introduced the **multitenant architecture**: a single **container database (CDB)** hosts one or more **pluggable databases (PDB)**. Before 12c, one instance = one database; now the instance-to-database relationship is 1:N.

Architecture:
- A CDB supports one or more PDBs; each PDB has its own copy of `SYSTEM` and application tablespaces.
- PDBs share the instance memory and background processes.
- A single **Root Container (CDB$ROOT)** holds redo logs, undo tablespace (unless 12.2 local undo mode), and control files.
- A single **Seed PDB** acts as a template for new PDBs.

**CDB** — created during 12c install; contains control files, system tablespaces, instance undo + redo logs; holds data dictionary for root and all PDBs.
**PDB** — independent database under a CDB; stores application data + its own data-dictionary metadata; created from `pdb$seed` or cloned from an existing PDB; has its own data files, system files, tablespaces, temp files.

Advantages: application isolation, portable schema collections, cloning/transport between CDBs, manage many DBs as one, separate security/users/resources per PDB, consolidation, easier patch/upgrade, container- and PDB-level backups.

Oracle 18c adds: DBCA PDB Clone, Refreshable PDB Switchover, CDB Fleet Management. Oracle 19 adds >1 PDB in a CDB in sharded environments.

```sql
SHOW PDBS;
-- CON_ID CON_NAME OPEN MODE   RESTRICTED
-- 2      PDB$SEED READ ONLY   NO
-- 3      PDB1     READ WRITE  NO

CREATE PLUGGABLE DATABASE PDB2 admin USER ora_admin
IDENTIFIED BY ora_admin FILE_NAME_CONVERT=('/pdbseed/','/pdb2/');

ALTER PLUGGABLE DATABASE PDB2 OPEN READ WRITE;

CREATE PLUGGABLE DATABASE PDB3
  FROM PDB2 FILE_NAME_CONVERT= ('/pdb2/','/pdb3/');
```

## PostgreSQL

Amazon Aurora PostgreSQL offers a simplified equivalent: create **multiple databases under one Aurora cluster**, and/or use **separate Aurora clusters** for full workload isolation. Each cluster has a primary (read/write) instance and up to **15 read-only nodes** for scale-out and HA.

Mapping: an Oracle **CDB/Instance ≈ an Aurora cluster**; an Oracle **PDB ≈ a PostgreSQL database** inside the cluster (not all features comparable).

Database cloning uses **templates** — set `IS_TEMPLATE` true, then create from it:
```sql
CREATE DATABASE emp_bck TEMPLATE emp;
```

Map Oracle 18c/19c features in AWS:
- **PDB Clone** → `CREATE DATABASE ... TEMPLATE ...`.
- **Refreshable PDB Switchover** → options by granularity: failover via `CREATE DATABASE` (same instance, when size/downtime allow) + app failover; database links or AWS DMS to keep two instances in sync + app failover; PostgreSQL **logical replication** for fine-grained replication (e.g. a single table).
- **CDB Fleet Management** → similar to AWS orchestration: manage multiple RDS instances (CDB) and their databases (PDB) centrally via console/CLI.

```sql
CREATE DATABASE pg_db1;
CREATE DATABASE pg_db2;
CREATE DATABASE pg_db3;

\l   -- list databases under the cluster
```

## Conversion notes
- No exact PDB equivalent. Use **multiple databases per Aurora cluster** for lightweight isolation, or **separate clusters** for total workload isolation.
- Each Aurora instance (primary/replica) has its own endpoint, enabling workload segmentation across replicas.
- Use the `TEMPLATE` option for cloning; use logical replication, database links, or AWS DMS to emulate refreshable/switchover scenarios.
- Centralized fleet management maps to managing RDS instances + databases via the AWS console/CLI.
