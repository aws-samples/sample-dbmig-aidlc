# Migration Guide — SQL Server → MySQL

> **Engine pair:** `sqlserver` (source) → `mysql` (target, Aurora MySQL compatible)
> **Engine definition:** [`engines/sqlserver-to-mysql/`](../engines/sqlserver-to-mysql/)
> **Playbook:** [`skills/sqlserver-to-mysql-playbook/`](../skills/sqlserver-to-mysql-playbook/)
>
> One of several engine-pair guides — see the [guides index](README.md). This pair reuses the
> existing **SQL Server source adapter** and **MySQL target adapter** — it required **no new
> Python code**, only an engine definition, a playbook, and this guide. That is the engine
> adapter pattern paying off.

A step-by-step guide to migrating a **Microsoft SQL Server** database to **MySQL** (Aurora
MySQL compatible) with **dbmig-aidlc**. The `dbmig` Python package does the deterministic
work; **Kiro performs the schema/T-SQL conversion** via the `db-migration-construction`
skill (the LLM is Kiro).

## 1. Prerequisites

- **Python 3.9+**; network access to the source SQL Server and target MySQL.
- Install deps (pure-Python drivers — no native clients):
  ```bash
  pip install -r scripts/requirements.txt   # oracledb, psycopg, pymysql, python-tds, pyyaml
  ```
- Run commands from the **repository root**.

## 2. Configure connections

```bash
cp templates/connections.example.yaml connections.yaml
cp templates/migration-config.example.yaml migration-config.yaml
```

Set source = SQL Server, target = MySQL (git-ignored files; use `${ENV_VAR}` for secrets):

```yaml
source:
  engine: sqlserver        # sqlserver | mssql | sql-server
  host: ${MSSQL_HOST}
  port: 1433
  database: ${MSSQL_DATABASE}
  username: ${MSSQL_USER}
  password: ${MSSQL_PASSWORD}

target:
  engine: mysql            # mysql | aurora-mysql
  host: ${MYSQL_HOST}
  port: 3306
  database: ${MYSQL_DATABASE}
  username: ${MYSQL_USER}
  password: ${MYSQL_PASSWORD}
  sslmode: require
```

The engine pair is detected automatically, so conversion uses the **SQL Server → MySQL**
datatype map and the **sqlserver-to-mysql-playbook** references. The SQL Server schema is
typically `dbo` — pass it as `--schema dbo`.

## 3. Run the migration

Conversationally: in Kiro say *"start a database migration from SQL Server to MySQL"* — the
orchestrator runs the phases with approval gates. Or drive the CLI:

```bash
python -m dbmig test-connection --side both
python -m dbmig inventory       --schema dbo --project myproject
python -m dbmig convert-schema  --schema dbo --project myproject
python -m dbmig apply-schema    --schema dbo --project myproject
python -m dbmig convert-code    --schema dbo --project myproject
python -m dbmig apply-schema    --schema dbo --project myproject --code
python -m dbmig migrate-data    --schema dbo --workers 8 --project myproject
python -m dbmig apply-schema    --schema dbo --project myproject --post-data
python -m dbmig compare         --schema dbo --project myproject
python -m dbmig gen-tests       --schema dbo --project myproject
python -m dbmig run-tests       --schema dbo --project myproject
```

The conversion hand-off, object-unit grouping, multi-pass apply, **error-retry loop**,
**silent/interactive run modes**, the follow-up log, and **equivalence testing** all work
exactly as in the [Oracle → PostgreSQL guide](oracle-to-postgresql.md) §5–§7. **Foreign keys
and triggers are deferred** and applied by `apply-schema --post-data` after the load; data is
loaded in **foreign-key dependency order** and `AUTO_INCREMENT` values are reset afterward
(OPG guide §5.3). Data is loaded via batched INSERT (MySQL has no COPY); for production-scale
movement use AWS DMS (`testing.data_load: dms`).

The SQL Server source DDL is reconstructed from the system catalogs by the `SQLServerEngine`
adapter (see the [SQL Server → PostgreSQL guide](sqlserver-to-postgresql.md) §3 for details).

## 4. SQL Server → MySQL specifics to expect

The conversion (Kiro, using the SQL Server→MySQL playbook + datatype map) accounts for these;
the validation phase tests for them:

- **Schema = `dbo`** → a MySQL **database**; identifiers use backticks; InnoDB; utf8mb4.
- **Case sensitivity**: SQL Server usually case-insensitive; MySQL depends on collation +
  `lower_case_table_names` — choose a collation matching the app (e.g. `utf8mb4_0900_ai_ci`).
- **IDENTITY → AUTO_INCREMENT** (one per table); `SCOPE_IDENTITY()` → `LAST_INSERT_ID()`.
- **No MERGE** → `INSERT ... ON DUPLICATE KEY UPDATE`; no sequences pre-8.0.
- **T-SQL → MySQL stored programs**; `TRY/CATCH` → `DECLARE ... HANDLER`.
- **Datatypes**: `money`→`decimal(19,4)`, `datetime`→`datetime(3)`, `bit`→`tinyint(1)`,
  `uniqueidentifier`→`char(36)`/`binary(16)`, `nvarchar(max)`→`longtext`; **`rowversion` is
  binary, not a datetime**.
- **Functions**: `GETDATE()`→`NOW()`, `ISNULL`→`IFNULL`/`COALESCE`, `LEN`→`CHAR_LENGTH`,
  `TOP n`→`LIMIT`, `+` concat → `CONCAT()`, `CHARINDEX`→`LOCATE`.
- **No equivalent / redesign**: CLR, Service Broker, linked servers, full-text search
  (MySQL FULLTEXT differs), columnstore, `hierarchyid`, `sql_variant`.
- MySQL DDL and procedures that `COMMIT` can't be rolled back during testing — test those
  only against a disposable target.

## 5. Reference

- Datatype mapping: [`engines/sqlserver-to-mysql/datatype-map.yaml`](../engines/sqlserver-to-mysql/datatype-map.yaml)
- Equivalence-testing spec: [`engines/sqlserver-to-mysql/checks/equivalence-spec.md`](../engines/sqlserver-to-mysql/checks/equivalence-spec.md)
- Conversion knowledge base: [`skills/sqlserver-to-mysql-playbook/`](../skills/sqlserver-to-mysql-playbook/)
- Command reference, run modes, follow-up, workspace artifacts, troubleshooting, safety:
  see the [Oracle → PostgreSQL guide](oracle-to-postgresql.md) §9–§12 (identical, with
  `sqlserver`/`1433` source and `mysql`/`3306` target engine values and `--schema dbo`).

> Reference only — the playbook references are distilled from the AWS *Microsoft SQL Server
> 2019 to Amazon Aurora MySQL Migration Playbook*. Test everything in a non-production
> environment first.

## Optional: convert the application too

After this migration, application code still speaks the source dialect. The opt-in
**app-modernization** module converts it — driven by this migration's own artifacts
(conversion log, validation carry-forwards) and the pair's `engines/sqlserver-to-mysql/app/` rules,
with a gated change plan before any edit and mirrored backups (never `.bak` files).
Start it explicitly: *"convert my application to work with the migrated database"*.
