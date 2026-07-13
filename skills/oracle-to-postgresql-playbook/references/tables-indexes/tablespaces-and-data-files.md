# Tablespaces and Data Files

> Source: AWS Oracle→Aurora PostgreSQL Migration Playbook
> URL: https://docs.aws.amazon.com/dms/latest/oracle-to-aurora-postgresql-migration-playbook/chap-oracle-aurora-pg.tables.tablespaces.html

**Conversion category:** Assisted (four-star feature compatibility)
**SCT automation:** N/A. All supported by PostgreSQL except managing the physical data files.

## Oracle
Oracle storage has physical and logical layers:
- **Tablespaces** — logical storage groups; containers for tables/indexes.
- **Data files** — physical files making up a tablespace (local FS, raw partitions, ASM, or NFS).

Storage hierarchy: Database → Tablespace → Data files → Segments → Extents → Blocks (smallest I/O unit).

Tablespace types: **Permanent**, **Undo** (manages UNDO in automatic undo mode), **Temporary** (session-scoped objects, sort spill).

Privileges: needs `CREATE TABLESPACE`; database must be in OPEN MODE.

```sql
CREATE TABLESPACE USERS
  DATAFILE '/u01/app/oracle/oradata/orcl/users01.dbf' SIZE 5242880
  AUTOEXTEND ON NEXT 1310720 MAXSIZE 32767M
  LOGGING ONLINE PERMANENT BLOCKSIZE 8192
  EXTENT MANAGEMENT LOCAL AUTOALLOCATE DEFAULT
  NOCOMPRESS SEGMENT SPACE MANAGEMENT AUTO;

DROP TABLESPACE USERS;
DROP TABLESPACE USERS INCLUDING CONTENTS AND DATAFILES;
```

## PostgreSQL
Similar concept but a **tablespace is a directory**; data files are FS files placed inside it, created automatically by PostgreSQL (akin to Oracle-Managed-Files). No user-configured segmentation into multiple separate data files. Each table/index is stored in a separate OS file named after its filenode number.

### Aurora PostgreSQL specifics
Two system tablespaces auto-provisioned, cannot be modified/dropped:
- `pg_global` — shared system catalogs, visible to all cluster databases.
- `pg_default` — default tablespace of `template1`/`template0`; default for new databases unless overridden.

When creating a tablespace, the superuser may specify an OS path that doesn't exist — it is implicitly created **under the embedded RDS/Aurora base path** `/rdsdbdata/tablespaces/`.

```sql
CREATE TABLESPACE TBS_01 LOCATION '/app_data/tbs_01';
-- \du shows location: /rdsdbdata/tablespaces/app_data/tbs_01

SELECT spcname, pg_tablespace_location(oid) FROM pg_tablespace;

DROP TABLESPACE TBS_01;

ALTER TABLESPACE TBS_01 RENAME TO IDX_TBS_01;
ALTER TABLESPACE TO IDX_TBS_01 OWNER TO USER1;

CREATE DATABASE DB1 TABLESPACE TBS_01;
CREATE TABLE TBL(COL1 NUMERIC, COL2 VARCHAR(10)) TABLESPACE TBS_01;
CREATE INDEX IDX_TBL ON TBL(COL1) TABLESPACE TBS_01;
ALTER TABLE TBL SET TABLESPACE TBS_02;
```

**Exceptions/privileges**: `CREATE TABLESPACE` can't run inside a transaction block; a tablespace can't be dropped until all objects in all databases using it are removed/moved; creation requires a superuser; afterward any user with sufficient privileges can use it.

**default_tablespace** parameter controls where new objects go (empty → `pg_default`); alter via cluster parameter group:
```sql
SET DEFAULT_TABLESPACE=TBS_01;
SHOW DEFAULT_TABLESPACE;   -- tbs_01
```

### Summary
| Feature | Oracle | Aurora PostgreSQL |
|---|---|---|
| Tablespace | Logical object from one+ data files | Logical object tied to a disk directory |
| Data file | User-created/resizable; OMF auto | OMF-like, auto-created in the tablespace dir; adds `_fsm` (free space map) and `_vm` (visibility map) files |
| New TS, system-managed files | `CREATE TABLESPACE sales_tbs DATAFILE SIZE 400M;` | `CREATE TABLESPACE sales_tbs LOCATION '/postgresql/data';` |
| New TS, user-managed files | `CREATE TABLESPACE sales_tbs DATAFILE '/oradata/sales01.dbf' SIZE 1M AUTOEXTEND ON NEXT 1M;` | N/A |
| Resize data file | `ALTER DATABASE DATAFILE '...' RESIZE 100M;` | N/A |
| Add data file | `ALTER TABLESPACE sales_tbs ADD DATAFILE '...' SIZE 10M;` | N/A |
| Per-database tablespace | 12c multi-tenant PDB default | `CREATE DATABASE sales OWNER sales_app TABLESPACE sales_tbs;` |
| Metadata tables | SYSTEM tablespace | pg_global tablespace |
| Encryption | TDE | AWS KMS keys (enabled at cluster deploy) |

## Conversion notes
- PostgreSQL/Aurora manages physical files automatically — drop Oracle data-file sizing/`AUTOEXTEND`/`RESIZE`/`ADD DATAFILE` management; there is no equivalent.
- A specified `LOCATION` is created under `/rdsdbdata/tablespaces/` in Aurora; you don't manage raw paths directly.
- Tablespaces are shared across all databases (set a per-database default instead of PDB-style isolation).
- `CREATE TABLESPACE` cannot run inside a transaction block and requires superuser.
- Encryption moves from Oracle TDE to AWS KMS-managed keys enabled at cluster creation.
