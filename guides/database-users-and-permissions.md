# Database users & permissions (source read-only, target read-write)

This guide is for anyone who is **not sure exactly which privileges the migration user needs**.
It shows how to create a **least-privilege read-only user on the source** and a
**read-write user on the target**, for every supported engine, plus the **extra permissions the
PostgreSQL FDW push-down method** (`migrate-data --method fdw`) requires.

It is engine-cutting; the per-pair guides (e.g.
[oracle-to-postgresql.md](oracle-to-postgresql.md)) reference this for the account setup and
otherwise focus on the workflow.

> ⚠️ **Non-production use.** This toolkit is designed for development, test, and
> proof-of-concept migrations — not production. Create these accounts on non-production
> databases, and have your DBA review any grants before applying them to a real system. See
> the repository [README](../README.md) and [DISCLAIMER.txt](../DISCLAIMER.txt).

---

## 1. What the framework actually does to each database

Grant only what these operations require:

| Phase / command | On the **source** | On the **target** |
|---|---|---|
| `test-connection`, `inventory`, `convert-schema`, `convert-code`, `gen-tests` | **read** catalog + object DDL + sample rows | — |
| `apply-schema` | — | **create** schemas, tables, indexes, constraints, sequences, routines, triggers |
| `migrate-data` (`toolkit`) | **read** table rows | **insert** rows (`COPY`/`INSERT`), `TRUNCATE` on `--truncate` |
| `migrate-data` (`fdw`, PostgreSQL target) | **read** table rows (as the source RO user, *via the target*) | create the FDW extension/server/foreign tables + **insert**; see §4 |
| `compare`, `run-tests` | **read**; `run-tests` also **executes** source routines (see the warning in §2) | read + write inside a rolled-back transaction |

The source side is **read-only by design** — with one important caveat about executing stored
routines, called out next.

---

## 2. Source: a read-only migration user

### ⚠️ Read-only on tables is *not* read-only if the user can execute routines that write

A user with no direct `INSERT`/`UPDATE`/`DELETE` grant can **still change data** if it is
allowed to **`EXECUTE` a procedure, function, or package that performs DML** (or DDL) — the
routine runs with its own privileges and modifies data on the caller's behalf.

This is not hypothetical for this framework: the **Validation phase (`run-tests`) executes
source functions and procedures** to compare their behaviour against the target. `run-tests`
wraps each call in a transaction and **rolls it back**, but:

- a routine that issues its **own `COMMIT`** (e.g. an Oracle *autonomous transaction*, or an
  explicit `COMMIT` in T-SQL) **cannot be undone** by the outer rollback, and
- any routine you invoke manually is subject to the same rule.

**Recommendation:** for a genuinely non-destructive source, **do not grant `EXECUTE`** on
stored routines to the read-only user, and skip procedure/function equivalence tests against
the live source — run them against a **disposable copy** instead. Grant `EXECUTE` only if you
have confirmed the routines are side-effect-free, or you accept the risk on a throwaway source.

### 2.1 Oracle source

```sql
-- Run as a DBA (e.g. the RDS master user).
CREATE USER dbmig_ro IDENTIFIED BY "<STRONG_PASSWORD>";
GRANT CREATE SESSION TO dbmig_ro;                 -- connect

-- Read the DATA of the schema(s) you migrate. Either broad:
GRANT SELECT ANY TABLE TO dbmig_ro;
--   ...or least-privilege, per object (repeat per table/view):
--   GRANT SELECT ON <SCHEMA>.<TABLE> TO dbmig_ro;

-- Read the CATALOG + object DDL (inventory + DBMS_METADATA.GET_DDL of other schemas).
GRANT SELECT_CATALOG_ROLE TO dbmig_ro;            -- ALL_* views + metadata

-- Do NOT grant EXECUTE on the app's packages/procedures/functions unless you have
-- read the warning above and accept it. (Omitted here on purpose.)
```

Notes:
- `SELECT_CATALOG_ROLE` is what lets `DBMS_METADATA.GET_DDL` return DDL for objects the user
  does not own; without it, DDL extraction for other schemas comes back empty.
- Prefer per-object `GRANT SELECT` over `SELECT ANY TABLE` when the source holds schemas you
  are **not** migrating.

### 2.2 SQL Server source

```sql
-- Server-level login (run in the master database as an admin / RDS master user):
CREATE LOGIN dbmig_ro WITH PASSWORD = '<STRONG_PASSWORD>';

-- Database-level user + read grants (run in EACH source database you migrate):
USE [<SOURCE_DATABASE>];
CREATE USER dbmig_ro FOR LOGIN dbmig_ro;
ALTER ROLE db_datareader ADD MEMBER dbmig_ro;     -- SELECT on all tables/views (data)
GRANT VIEW DEFINITION TO dbmig_ro;                -- read routine/view/table definitions (DDL)
GRANT VIEW DATABASE STATE TO dbmig_ro;            -- catalog/stats for inventory & row estimates

-- Again: do NOT grant EXECUTE on procedures/functions unless you accept the warning above.
```

Notes:
- `db_datareader` + `VIEW DEFINITION` covers the adapter's catalog-based DDL reconstruction
  (`INFORMATION_SCHEMA`, `sys.*`, `OBJECT_DEFINITION`, `sys.sql_modules`).
- For the **FDW method**, the SQL Server user needs one more grant — see §4.2.

---

## 3. Target: the database and a read-write migration user

On managed services (Amazon RDS / Aurora) the **master user is created with the instance**;
these steps create a *dedicated* migration user with just what `apply-schema` and
`migrate-data` need. Run them as the master user (or a DBA).

### 3.1 PostgreSQL / Aurora PostgreSQL target

```sql
-- If the database does not already exist:
CREATE DATABASE <TARGET_DB>;

-- Dedicated login role:
CREATE ROLE dbmig_rw LOGIN PASSWORD '<STRONG_PASSWORD>';
GRANT CONNECT ON DATABASE <TARGET_DB> TO dbmig_rw;

-- Let it create and own the target schema(s) it will populate:
\connect <TARGET_DB>
CREATE SCHEMA <TARGET_SCHEMA> AUTHORIZATION dbmig_rw;   -- owner => full rights within the schema
-- (or, to let it create schemas itself:  GRANT CREATE ON DATABASE <TARGET_DB> TO dbmig_rw; )
```

That is sufficient for the **`toolkit`** method: as owner of `<TARGET_SCHEMA>`, `dbmig_rw`
can create tables/indexes/constraints/sequences/routines/triggers and `COPY`/`INSERT` rows
(`COPY … FROM STDIN` needs only `INSERT`, **not** superuser). For the **`fdw`** method, see §4.1.

### 3.2 MySQL / Aurora MySQL target

```sql
CREATE DATABASE <TARGET_DB> CHARACTER SET utf8mb4;

CREATE USER 'dbmig_rw'@'%' IDENTIFIED BY '<STRONG_PASSWORD>';
GRANT CREATE, ALTER, DROP, INDEX, REFERENCES,
      INSERT, SELECT, UPDATE, DELETE,
      CREATE VIEW, SHOW VIEW,
      CREATE ROUTINE, ALTER ROUTINE, EXECUTE,
      TRIGGER
  ON <TARGET_DB>.* TO 'dbmig_rw'@'%';
FLUSH PRIVILEGES;
```

Notes:
- `DROP` is required because MySQL `TRUNCATE` (used by `migrate-data --truncate`) needs it.
- Restrict `'%'` to the host/CIDR your `dbmig` host connects from where possible.
- **MySQL has no heterogeneous FDW**, so the `fdw` method does not apply to a MySQL target;
  use `toolkit` (or AWS DMS).

---

## 4. Extra permissions for the FDW push-down method (PostgreSQL target only)

`migrate-data --method fdw` makes the **target** PostgreSQL read directly from the source via
`oracle_fdw` (Oracle) or `tds_fdw` (SQL Server). That adds permission requirements the
`toolkit` method does not have.

### 4.1 On the target (PostgreSQL)

1. **Install the wrapper extension — requires `rds_superuser`** (RDS/Aurora do not grant true
   `SUPERUSER`; the **master user is `rds_superuser`**):
   ```sql
   CREATE EXTENSION IF NOT EXISTS oracle_fdw;   -- or: tds_fdw
   ```
2. **Create the server + user mapping + foreign tables.** The role that runs the load needs to
   create a `FOREIGN SERVER` (which requires `USAGE` on the foreign-data-wrapper), a
   `USER MAPPING FOR CURRENT_USER`, and a staging schema `dbmig_fdw_<schema>` with foreign
   tables in the target database.

   - **Simplest (recommended for dev/test):** run the `fdw` load as the **RDS master user**
     (`rds_superuser`) — it already has everything above, including creating the extension.
   - **Least-privilege:** have an `rds_superuser` pre-create the extension (step 1) and then
     grant a dedicated role the rest:
     ```sql
     GRANT USAGE ON FOREIGN DATA WRAPPER oracle_fdw TO dbmig_rw;  -- lets it CREATE SERVER
     GRANT CREATE ON DATABASE <TARGET_DB> TO dbmig_rw;            -- lets it create the staging schema
     -- dbmig_rw must also own / be able to INSERT into the target tables (see §3.1).
     ```

> 🔐 **Security note.** The FDW `USER MAPPING` stores the **source user's credentials inside
> the target** catalog. The framework therefore **drops the FDW server + staging schema by
> default** after the load (removing those credentials); use `--fdw-keep` only when you must,
> and `--fdw-cleanup` to remove them afterwards. This is another reason the source user should
> be **least-privilege read-only** (§2).

### 4.2 On the source (extra grant for SQL Server)

`tds_fdw`'s foreign tables use `row_estimate_method 'showplan_all'`, which needs the
`SHOWPLAN` permission for the source user in each migrated database:

```sql
USE [<SOURCE_DATABASE>];
GRANT SHOWPLAN TO dbmig_ro;
```

Oracle (`oracle_fdw`) needs no extra source grant beyond the `SELECT` in §2.1.

### 4.3 Networking

For the `fdw` method the **target database must be able to reach the source** on its DB port
(the load runs *inside* the target). Ensure the source's security group / firewall allows
inbound from the target — e.g. on RDS, add the source DB's security group an ingress rule for
the source port (Oracle `1521`, SQL Server `1433`) from the target's VPC/CIDR or security
group. (The `toolkit` method instead needs the **`dbmig` host** to reach *both* databases.)

---

## 5. Point the connection file at these users

In `connections.yaml`, the **`source`** block uses the read-only user and the **`target`**
block uses the read-write user. Keep secrets out of the file with `${ENV_VAR}` references:

```yaml
source:
  engine: oracle            # or sqlserver
  host: ${SRC_HOST}
  port: 1521                # 1433 for SQL Server
  service_name: ${SRC_SERVICE}   # (Oracle) or sid: ; (SQL Server) database: ${SRC_DB}
  username: ${SRC_USER}     # dbmig_ro
  password: ${SRC_PASSWORD}

target:
  engine: postgresql        # or mysql
  host: ${TGT_HOST}
  port: 5432                # 3306 for MySQL
  database: ${TGT_DB}
  username: ${TGT_USER}     # dbmig_rw  (for --method fdw, see §4.1 on rds_superuser)
  password: ${TGT_PASSWORD}
  default_schema: <TARGET_SCHEMA>
  sslmode: require
```

See [templates/connections.example.yaml](../templates/connections.example.yaml) for the full,
commented template (including TLS options).

---

## 6. Verify the accounts

```bash
python -m dbmig test-connection --side both   # exits non-zero on failure
```

A successful run prints the server versions for both sides. If you plan to use `--method fdw`,
also confirm the wrapper is installable on the target (as `rds_superuser`):

```sql
SELECT name, default_version FROM pg_available_extensions
WHERE name IN ('oracle_fdw','tds_fdw');
```

---

## Related

- Per-pair walkthroughs: [oracle-to-postgresql.md](oracle-to-postgresql.md) ·
  [oracle-to-mysql.md](oracle-to-mysql.md) ·
  [sqlserver-to-postgresql.md](sqlserver-to-postgresql.md) ·
  [sqlserver-to-mysql.md](sqlserver-to-mysql.md)
- Encryption in transit and secret handling: [../SECURITY.md](../SECURITY.md)
- FDW push-down method details and throughput: [../benchmarks/data-migration-speed.md](../benchmarks/data-migration-speed.md)
