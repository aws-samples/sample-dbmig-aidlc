# Migration Guide — Oracle → MySQL

> **Engine pair:** `oracle` (source) → `mysql` (target, Aurora MySQL compatible)
> **Engine definition:** [`engines/oracle-to-mysql/`](../engines/oracle-to-mysql/)
> **Playbook:** [`skills/oracle-to-mysql-playbook/`](../skills/oracle-to-mysql-playbook/)
>
> One of several engine-pair guides — see the [guides index](README.md). The orchestration,
> the `dbmig` CLI, and the AI-DLC lifecycle are identical to the other pairs; only the engine
> definition, the playbook references, and the target driver differ.

A step-by-step guide to migrating an **Oracle** schema to **MySQL** (Aurora MySQL compatible)
with **dbmig-aidlc**. The `dbmig` Python package does the deterministic work; **Kiro performs
the schema conversion** via the `db-migration-construction` skill (the LLM is Kiro).

## 1. Prerequisites

- **Python 3.9+**; network access to the source Oracle and target MySQL/Aurora MySQL.
- Install deps (pure-Python drivers — no native clients):
  ```bash
  pip install -r scripts/requirements.txt   # oracledb, psycopg, pymysql, pyyaml
  ```
- Run commands from the **repository root**.

## 2. Configure connections

```bash
cp templates/connections.example.yaml connections.yaml
cp templates/migration-config.example.yaml migration-config.yaml
```

Set the target to MySQL (both files are git-ignored; use `${ENV_VAR}` for secrets):

```yaml
source:
  engine: oracle
  host: ${ORA_HOST}
  port: 1521
  service_name: ${ORA_SERVICE}
  username: ${ORA_USER}
  password: ${ORA_PASSWORD}

target:
  engine: mysql            # mysql | aurora-mysql
  host: ${MYSQL_HOST}
  port: 3306
  database: ${MYSQL_DATABASE}
  username: ${MYSQL_USER}
  password: ${MYSQL_PASSWORD}
  sslmode: require         # require enables TLS; 'disable' turns it off
```

In `migration-config.yaml`, set the schema(s) and (optionally) `run.mode` and `llm.max_retries`.
The engine pair is detected automatically from the connection engines, so conversion uses the
**Oracle→MySQL** datatype map and the **oracle-to-mysql-playbook** references.

## 3. Run the migration

Conversationally: in Kiro say *"start a database migration from Oracle to MySQL"* — the
orchestrator runs the phases with approval gates. Or drive the CLI:

```bash
python -m dbmig test-connection --side both
python -m dbmig inventory       --schema APP --project myproject

# Construction — Kiro converts each object-unit to MySQL DDL, then apply (auto error-retry)
python -m dbmig convert-schema  --schema APP --project myproject
python -m dbmig apply-schema    --schema APP --project myproject
python -m dbmig convert-code    --schema APP --project myproject
python -m dbmig apply-schema    --schema APP --project myproject --code

# Data + validation (foreign keys + triggers are deferred to --post-data, after the load)
python -m dbmig migrate-data    --schema APP --workers 8 --project myproject
python -m dbmig apply-schema    --schema APP --project myproject --post-data
python -m dbmig compare         --schema APP --project myproject
python -m dbmig gen-tests       --schema APP --project myproject
python -m dbmig run-tests       --schema APP --project myproject
```

The conversion hand-off, object-unit grouping, multi-pass apply, **error-retry loop**
(`RETRY_AVAILABLE`/`MAX_RETRIES_EXHAUSTED`), **silent/interactive run modes**, the follow-up
log, and **equivalence testing** (functions/procedures, real data, rolled-back transaction)
all work exactly as in the [Oracle → PostgreSQL guide](oracle-to-postgresql.md) §5–§7 —
re-read those sections for the mechanics. **Foreign keys and triggers are deferred** and
applied by `apply-schema --post-data` after the load; data is loaded in **foreign-key
dependency order** and identity/`AUTO_INCREMENT` values are reset afterward (OPG guide §5.3).
Data is loaded with batched `INSERT` (MySQL has no COPY); for production-scale movement use
AWS DMS (`testing.data_load: dms`).

## 4. MySQL-specific things to expect

The conversion (done by Kiro using the MySQL playbook + datatype map) accounts for these; the
validation phase tests for them:

- **A MySQL schema is a database.** The Oracle schema (lower-cased) maps to a MySQL database;
  `apply-schema` issues `CREATE DATABASE IF NOT EXISTS`. Tables are referenced
  `` `db`.`table` ``.
- **Identifiers** use backticks; **InnoDB** is the storage engine; charset **utf8mb4**.
- **No packages** — each public subprogram becomes its own stored routine, named
  `<package>_<subprogram>`. `convert-code` flags cases where that underscore-join collides
  (two routines mapping to one name) — see the OPG guide and `engines/*/checks/package-naming.md`.
- **No `MERGE`** — converted to `INSERT ... ON DUPLICATE KEY UPDATE`.
- **No sequences pre-8.0** — Oracle sequences map to `AUTO_INCREMENT` (one per table); shared
  or multi-sequence logic needs redesign (flagged for follow-up).
- **Dates**: Oracle `DATE` → `datetime`; date arithmetic uses `DATE_ADD(... INTERVAL ...)`.
- **`TIMESTAMP WITH TIME ZONE`** has no native MySQL type — verify tz handling.
- **Empty string `''`** is not NULL in MySQL (it is in Oracle).
- **`ROWID`/`BFILE`/`UROWID`** unsupported — redesign dependent logic.
- **DDL auto-commits** in MySQL; a procedure that issues `COMMIT` can't be rolled back during
  testing — test those only against a disposable target.

## 5. Reference

- Datatype mapping: [`engines/oracle-to-mysql/datatype-map.yaml`](../engines/oracle-to-mysql/datatype-map.yaml)
- Equivalence-testing spec: [`engines/oracle-to-mysql/checks/equivalence-spec.md`](../engines/oracle-to-mysql/checks/equivalence-spec.md)
- Conversion knowledge base: [`skills/oracle-to-mysql-playbook/`](../skills/oracle-to-mysql-playbook/)
- Command reference, run modes, follow-up, workspace artifacts, troubleshooting, safety:
  see the [Oracle → PostgreSQL guide](oracle-to-postgresql.md) §9–§12 (identical for MySQL,
  with `database`/`3306`/`mysql` engine values).

> Reference only — the playbook references are distilled from the AWS *Oracle to Aurora MySQL
> Migration Playbook*. Test everything in a non-production environment first.
